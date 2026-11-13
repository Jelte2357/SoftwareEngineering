import os
from pathlib import Path

import pika

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

JOB_QUEUE = os.getenv("RABBITMQ_QUEUE", "prediction_jobs")

CONNECTION_PARAMETERS = pika.ConnectionParameters(
    host=os.getenv("RABBITMQ_HOST", "localhost"),
    port=int(os.getenv("RABBITMQ_PORT", "5672")),
    credentials=pika.PlainCredentials(
        os.getenv("RABBITMQ_USER", "guest"),
        os.getenv("RABBITMQ_PASSWORD", "guest"),
    ),
    heartbeat=60,
    blocked_connection_timeout=30,
)