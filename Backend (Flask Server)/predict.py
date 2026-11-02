from __future__ import annotations
import argparse
import os
from pathlib import Path
from typing import Sequence
import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = Path(
    os.getenv(
        "MODEL_DIR",
        str(BASE_DIR / "outputs" / "distilbert_classifier")
    )
).expanduser()

MAX_LENGTH = int(os.getenv("MAX_LENGTH", "256"))
INFERENCE_BATCH_SIZE = int(
    os.getenv("INFERENCE_BATCH_SIZE", "64")
)
class HateSpeechPredictor:
    """
    Reusable inference object.
    Loads the tokenizer and model during initialization.
    """
    def __init__(
        self,
        model_dir: Path = MODEL_DIR,
        max_length: int = MAX_LENGTH,
        batch_size: int = INFERENCE_BATCH_SIZE,
    ) -> None:
        model_dir = Path(model_dir).expanduser()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_dir,
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_dir
        )
        self.model.to(self.device)
        self.model.eval()
        
        self.max_length = max_length
        self.batch_size = batch_size

    def predict(
        self,
        texts: Sequence[str]
    ) -> list[dict[str, float | int]]:
        """
        Predict multiple texts and return probabilities.
        """
        results = []
        with torch.inference_mode():
            for start in range(
                0,
                len(texts),
                self.batch_size
            ):
                batch_texts = list(texts[start:start + self.batch_size])
                encoded = self.tokenizer(
                    batch_texts,
                    truncation=True,
                    max_length=self.max_length,
                    padding=True,
                    return_tensors="pt",
                )
                encoded = {
                    key: value.to(self.device)
                    for key, value in encoded.items()
                }
                logits = self.model(**encoded).logits
                probabilities = torch.softmax(
                    logits,
                    dim=-1
                ).cpu().tolist()
                for probability in probabilities:
                    predicted_label = max(
                        range(len(probability)),
                        key=probability.__getitem__
                    )
                    results.append(float(probability[1]))
        return results