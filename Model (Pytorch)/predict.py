"""Run predictions using the model saved by train_distilbert.py."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import time

MODEL_DIR = Path("outputs/distilbert_classifier")
MAX_LENGTH = 256
INFERENCE_BATCH_SIZE = 32


def predict(texts: Sequence[str], model_dir: Path = MODEL_DIR) -> list[dict[str, float | int]]:
    if not texts:
        return []
    if not model_dir.exists():
        raise FileNotFoundError(
            f"Model directory not found: {model_dir.resolve()}. Run train_distilbert.py first."
        )

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    results: list[dict[str, float | int]] = []
    with torch.inference_mode():
        st = time.perf_counter()
        for start in range(0, len(texts), INFERENCE_BATCH_SIZE):
            batch_texts = list(texts[start : start + INFERENCE_BATCH_SIZE])
            encoded = tokenizer(
                batch_texts,
                truncation=True,
                max_length=MAX_LENGTH,
                padding=True,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            logits = model(**encoded).logits
            probabilities = torch.softmax(logits, dim=-1)
            scores, labels = probabilities.max(dim=-1)
            for probability, label, score in zip(
                probabilities.cpu().tolist(), labels.cpu().tolist(), scores.cpu().tolist()
            ):
                results.append(
                    {
                        "label": int(label),
                        "confidence": float(score),
                        "label_0_confidence": float(probability[0]),
                        "label_1_confidence": float(probability[1]),
                    }
                )
        et = time.perf_counter()
        print(f"Predictions completed in {et - st:.2f} seconds.")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict labels for text with DistilBERT.")
    parser.add_argument(
        "--text",
        action="append",
        required=True,
        help="Text to classify. Repeat --text to classify multiple examples.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=MODEL_DIR,
        help="Directory containing the trained Hugging Face model.",
    )
    args = parser.parse_args()

    texts = args.text
    
    # import pandas as pd
    # data = pd.read_csv("data.csv")
    # sample = data.sample(n=5000, random_state=42)
    # texts = sample["text"].tolist()
    
    
    predictions = predict(texts, args.model_dir)

    for text, result in zip(texts, predictions):
        print(f"text: {text}")
        print(f"predicted_label: 0  confidence: {result['label_0_confidence']:.4f}")
        print(f"predicted_label: 1  confidence: {result['label_1_confidence']:.4f}")
        print()


if __name__ == "__main__":
    main()
