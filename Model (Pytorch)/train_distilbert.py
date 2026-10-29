"""Train a DistilBERT binary text classifier from a CSV with columns: text,label.

Windows-friendly defaults: DataLoader(num_workers=0), disk-backed HF Datasets,
256-token truncation, dynamic padding, mixed precision on CUDA, and checkpoints.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import lightning as L
import numpy as np
import torch
from datasets import DatasetDict, load_dataset, load_from_disk
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader
from torchmetrics.classification import MulticlassF1Score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    get_linear_schedule_with_warmup,
)

# ----------------------------- Configuration -----------------------------
CSV_PATH = Path("data.csv")  # Put your CSV beside this script, or change this path.
MODEL_NAME = "distilbert/distilbert-base-uncased"
MAX_LENGTH = 256
VALIDATION_FRACTION = 0.05
SEED = 42

BATCH_SIZE = 16                 # Reduce to 8 or 4 if you run out of GPU memory.
GRADIENT_ACCUMULATION = 2       # Effective batch size = 16 * 2 = 32.
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01
MAX_EPOCHS = 3
MAX_TRAIN_EXAMPLES: int | None = 50_000 # None  # Set to 50_000 for a quick run; None uses all training rows.

CACHE_ROOT = Path("cache")
OUTPUT_DIR = Path("outputs")
FINAL_MODEL_DIR = OUTPUT_DIR / "distilbert_classifier"
NUM_WORKERS = 0                 # Safe default for Windows.


class DistilBERTLightningModule(L.LightningModule):
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        num_labels: int = 2,
        learning_rate: float = LEARNING_RATE,
        weight_decay: float = WEIGHT_DECAY,
    ) -> None:
        super().__init__()
        self.save_hyperparameters()
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, num_labels=num_labels
        )
        self.model.config.id2label = {0: "0", 1: "1"}
        self.model.config.label2id = {"0": 0, "1": 1}
        self.val_f1 = MulticlassF1Score(num_classes=num_labels, average="macro")

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> Any:
        return self.model(input_ids=input_ids, attention_mask=attention_mask)

    def training_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> torch.Tensor:
        outputs = self.model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            labels=batch["labels"],
        )
        self.log(
            "train_loss",
            outputs.loss,
            on_step=True,
            on_epoch=True,
            prog_bar=True,
            batch_size=batch["labels"].size(0),
        )
        return outputs.loss

    def validation_step(self, batch: dict[str, torch.Tensor], batch_idx: int) -> None:
        outputs = self.model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            labels=batch["labels"],
        )
        predictions = outputs.logits.argmax(dim=-1)
        self.val_f1.update(predictions, batch["labels"])
        self.log(
            "val_loss",
            outputs.loss,
            on_step=False,
            on_epoch=True,
            prog_bar=True,
            batch_size=batch["labels"].size(0),
        )
        self.log("val_f1", self.val_f1, on_step=False, on_epoch=True, prog_bar=True)

    def configure_optimizers(self) -> dict[str, Any]:
        optimizer = torch.optim.AdamW(
            self.parameters(),
            lr=self.hparams.learning_rate,
            weight_decay=self.hparams.weight_decay,
        )
        total_steps = self.trainer.estimated_stepping_batches
        warmup_steps = int(0.06 * total_steps)
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=warmup_steps,
            num_training_steps=total_steps,
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {"scheduler": scheduler, "interval": "step"},
        }


def _cache_path(csv_path: Path) -> Path:
    """Change the cache path when the input file's size or modification time changes."""
    stat = csv_path.stat()
    model_slug = MODEL_NAME.replace("/", "_")
    return CACHE_ROOT / (
        f"{csv_path.stem}_{stat.st_size}_{stat.st_mtime_ns}_{model_slug}_max{MAX_LENGTH}"
    )


def prepare_datasets(csv_path: Path, tokenizer: Any) -> DatasetDict:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Cannot find {csv_path.resolve()}. Put data.csv beside this script "
            "or update CSV_PATH near the top of train_distilbert.py."
        )

    cache_dir = _cache_path(csv_path)
    cache_complete = (cache_dir / "dataset_dict.json").exists()
    if cache_complete:
        print(f"Loading cached, tokenized data from: {cache_dir}")
        return load_from_disk(str(cache_dir))
    if cache_dir.exists():
        # Recover from an interrupted preprocessing run.
        shutil.rmtree(cache_dir)

    print(f"Reading CSV: {csv_path.resolve()}")
    raw = load_dataset("csv", data_files=str(csv_path), split="train")
    # Tolerate headers such as "text, label" with a leading space before label.
    stripped_names = {name: name.strip() for name in raw.column_names}
    if any(old != new for old, new in stripped_names.items()):
        raw = raw.rename_columns(stripped_names)
    required = {"text", "label"}
    missing = required.difference(raw.column_names)
    if missing:
        raise ValueError(
            f"CSV must contain columns named 'text' and 'label'. Missing: {sorted(missing)}. "
            f"Found columns: {raw.column_names}"
        )

    # Remove empty texts and missing labels. Extra CSV columns are ignored.
    raw = raw.filter(
        lambda row: row["text"] is not None
        and row["label"] is not None
        and str(row["text"]).strip() != "",
        desc="Removing empty rows",
    )
    raw = raw.remove_columns([c for c in raw.column_names if c not in ("text", "label")])

    def normalize_labels(batch: dict[str, list[Any]]) -> dict[str, list[int]]:
        clean_labels: list[int] = []
        for value in batch["label"]:
            numeric = float(value)
            label = int(numeric)
            if numeric != label:
                raise ValueError(f"Expected integer class labels 0/1, found {value!r}.")
            if label not in (0, 1):
                raise ValueError(f"Expected binary class labels 0/1, found {label}.")
            clean_labels.append(label)
        return {"label": clean_labels}

    raw = raw.map(normalize_labels, batched=True, desc="Validating labels")
    if len(raw) < 2:
        raise ValueError("Not enough valid rows to create train/validation splits.")

    labels = np.asarray(raw["label"], dtype=np.int64)
    classes, counts = np.unique(labels, return_counts=True)
    if len(classes) != 2:
        raise ValueError(f"Both labels 0 and 1 must be present. Found: {dict(zip(classes.tolist(), counts.tolist()))}")
    print(f"Usable examples: {len(raw):,}; label counts: {dict(zip(classes.tolist(), counts.tolist()))}")

    train_indices, val_indices = train_test_split(
        np.arange(len(raw)),
        test_size=VALIDATION_FRACTION,
        random_state=SEED,
        stratify=labels,
    )
    train_raw = raw.select(train_indices)
    val_raw = raw.select(val_indices)

    def tokenize_batch(batch: dict[str, list[str]]) -> dict[str, Any]:
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=MAX_LENGTH,
            padding=False,  # Pad per batch below to avoid wasted compute.
        )

    train_tokens = train_raw.map(
        tokenize_batch,
        batched=True,
        batch_size=1000,
        remove_columns=["text"],
        desc=f"Tokenizing training data (max {MAX_LENGTH} tokens)",
    )
    val_tokens = val_raw.map(
        tokenize_batch,
        batched=True,
        batch_size=1000,
        remove_columns=["text"],
        desc=f"Tokenizing validation data (max {MAX_LENGTH} tokens)",
    )

    tokenized = DatasetDict({"train": train_tokens, "validation": val_tokens})
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    tokenized.save_to_disk(str(cache_dir))
    print(f"Saved tokenized cache to: {cache_dir}")
    return tokenized


def main() -> None:
    L.seed_everything(SEED, workers=True)
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
    datasets = prepare_datasets(CSV_PATH, tokenizer)

    # On CUDA, padding to a multiple of 8 can improve mixed-precision throughput.
    train_dataset = datasets["train"]
    if MAX_TRAIN_EXAMPLES is not None:
        if MAX_TRAIN_EXAMPLES < 2:
            raise ValueError("MAX_TRAIN_EXAMPLES must be at least 2, or None for all rows.")
        if MAX_TRAIN_EXAMPLES < len(train_dataset):
            subset_labels = np.asarray(train_dataset["label"], dtype=np.int64)
            selected, _ = train_test_split(
                np.arange(len(train_dataset)),
                train_size=MAX_TRAIN_EXAMPLES,
                random_state=SEED,
                stratify=subset_labels,
            )
            train_dataset = train_dataset.select(selected)
            print(f"Quick-run mode: training on a stratified subset of {len(train_dataset):,} examples.")

    collator = DataCollatorWithPadding(
        tokenizer=tokenizer,
        padding=True,
        pad_to_multiple_of=8 if torch.cuda.is_available() else None,
        return_tensors="pt",
    )
    pin_memory = torch.cuda.is_available()
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=collator,
        num_workers=NUM_WORKERS,
        pin_memory=pin_memory,
    )
    val_loader = DataLoader(
        datasets["validation"],
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=collator,
        num_workers=NUM_WORKERS,
        pin_memory=pin_memory,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_callback = ModelCheckpoint(
        dirpath=str(OUTPUT_DIR / "checkpoints"),
        filename="epoch={epoch:02d}-val_f1={val_f1:.4f}",
        monitor="val_f1",
        mode="max",
        save_top_k=1,
        save_last=True,
        auto_insert_metric_name=False,
    )
    early_stopping = EarlyStopping(
        monitor="val_f1", mode="max", patience=2, min_delta=0.001
    )

    model = DistilBERTLightningModule()
    use_gpu = torch.cuda.is_available()
    trainer = L.Trainer(
        accelerator="gpu" if use_gpu else "cpu",
        devices=1,
        precision="16-mixed" if use_gpu else "32-true",
        max_epochs=MAX_EPOCHS,
        accumulate_grad_batches=GRADIENT_ACCUMULATION,
        gradient_clip_val=1.0,
        callbacks=[checkpoint_callback, early_stopping],
        log_every_n_steps=50,
        num_sanity_val_steps=0,
        enable_progress_bar=True,
    )

    print(
        f"Training on {'CUDA GPU' if use_gpu else 'CPU'} | batch={BATCH_SIZE} | "
        f"gradient accumulation={GRADIENT_ACCUMULATION} | "
        f"effective batch={BATCH_SIZE * GRADIENT_ACCUMULATION} | max tokens={MAX_LENGTH}"
    )
    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)

    best_checkpoint = checkpoint_callback.best_model_path
    if not best_checkpoint:
        raise RuntimeError("No best checkpoint was produced; check validation metrics/logs.")
    print(f"Best Lightning checkpoint: {best_checkpoint}")

    best_model = DistilBERTLightningModule.load_from_checkpoint(best_checkpoint, map_location="cpu")
    FINAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    best_model.model.save_pretrained(FINAL_MODEL_DIR)
    tokenizer.save_pretrained(FINAL_MODEL_DIR)
    print(f"Hugging Face model and tokenizer saved to: {FINAL_MODEL_DIR.resolve()}")
    print("Use predict.py to run predictions with the saved model.")


if __name__ == "__main__":
    main()
