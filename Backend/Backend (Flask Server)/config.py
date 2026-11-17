import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = Path(
    os.getenv(
        "MODEL_DIR",
        str(BASE_DIR / "outputs" / "distilbert_classifier")
    )
).expanduser()

DB_PATH = Path(
    os.getenv(
        "DB_PATH",
        str(BASE_DIR / "hashes.db")
    )
).expanduser()

MAX_BATCH_SIZE = int(
    os.getenv("MAX_BATCH_SIZE", "128")
)

MAX_REQUEST_LENGTH = int(
    os.getenv("MAX_REQUEST_LENGTH", "5000")
)