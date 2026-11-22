"""RabbitMQ worker for hate-speech prediction and user reclassification.

This module loads the configured DistilBERT predictor and SQLite database,
implements the prediction and feedback tasks, and consumes jobs from the
RabbitMQ queue configured in config.py. Results are returned through the
reply queue supplied with each message. Run this module to start the worker."""

import hashlib
from predict import HateSpeechPredictor
from config import *
from database import Database
import normalize
from typing import cast

import pika
import json
import os
import time

classifier = HateSpeechPredictor(
    model_dir=MODEL_DIR,
)

db = Database(db_path=DB_PATH)

def predict_texts(texts: tuple[str]) -> list[float]:
    """Predict scores for normalized texts, reusing cached results where possible.

    Args:
        texts: Tuple of input strings. Repeated strings are deduplicated for lookup
            and inference, while the returned list preserves the original order
            and multiplicity.

    Returns:
        One probability score per input string, in the same order as ``texts``.

    Notes:
        Text is hashed with BLAKE2b. The database lock covers cache lookup,
        inference for cache misses, and insertion of newly calculated scores."""
    unique_texts = dict.fromkeys(texts)  # Remove duplicates while preserving order
    text_to_hash = {text: hashlib.blake2b(text.encode("utf-8")).hexdigest() for text in unique_texts}
    hash_to_text = {hash: text for text, hash in text_to_hash.items()}

    with db.lock:
        known, missing = db.get_scores(list(hash_to_text.keys()))
        known_predictions = {hash_to_text[hash]: score for hash, score in known.items()}
        missing_predictions = {}
        if missing:
            missing_texts = [hash_to_text[hash] for hash in missing]
            missing_predictions = dict(zip(missing_texts, classifier.predict(missing_texts)))
            db.insert_scores({text_to_hash[text]: score for text, score in missing_predictions.items()})
    
    all_predictions = {**known_predictions, **missing_predictions}
    return [all_predictions[text] for text in texts]

def predict(payload: dict) -> dict:
    """Normalize a keyed payload and classify each supplied text.

    Args:
        payload: Mapping-like dictionary whose keys identify texts and whose
            values are the input strings.

    Returns:
        Dictionary mapping each original payload key to its prediction score.

    Notes:
        The values are processed with normalize.normalize_all_apply before the
        cache/inference stage. The original keys are retained in the result."""
    keys, texts = zip(*payload.items())
    texts = cast(tuple[str], tuple(map(normalize.normalize_all_apply, texts)))
    predictions = predict_texts(texts)
    results = dict(zip(keys, predictions))
    return results

def reclassify(payload: dict) -> dict:
    """Store a user-provided reclassification flag for a text hash.

    Args:
        payload: Dictionary containing ``text`` and ``flag`` fields.

    Returns:
        Dictionary containing the BLAKE2b hash, supplied flag, and save message.

    Notes:
        This operation records feedback in hash_flags. It does not retrain the
        model or update the cached prediction score."""
    text = payload["text"]
    flag = bool(payload["flag"])
    
    text_hash = hashlib.blake2b(text.encode("utf-8")).hexdigest()
    
    with db.lock:
        db.insert_flag(text_hash, flag) 
    
    return {"hash": text_hash, "flag": payload["flag"], "message": "saved"}

def callback(ch, method, properties, body):
    """Handle one RabbitMQ job and publish its result to the reply queue.

    Args:
        ch: Pika channel used to publish the response and acknowledge the job.
        method: Delivery metadata, including the message delivery tag.
        properties: AMQP properties containing correlation and reply information.
        body: UTF-8 encoded JSON job message.

    Notes:
        Supported task names are ``predict`` and ``reclassify``. Exceptions are
        converted into an error response. The delivery is acknowledged after the
        response-publishing attempt."""
    job_id = properties.correlation_id
    started = time.perf_counter()

    try:
        job = json.loads(body)
        task = job.get("task")
        payload = job.get("payload")

        # 2 very simple checks because otherwise my static type checker gets mad at me
        assert isinstance(payload, dict), ValueError("Job payload must be a dictionary.")
        assert isinstance(task, str) and task in {"predict", "reclassify"}, ValueError("Job task must be 'predict' or 'reclassify'.")

        if task == "predict":
            result = predict(payload)
        elif task == "reclassify":
            result = reclassify(payload)
        else:
            raise ValueError(f"Unknown task: {task}") # Won't ever happen but static typechecker
            
        response = {"result": result}
        print(job_id, time.perf_counter() - started)

    except Exception as e:
        response = {"error": str(e)}

    if properties.reply_to and properties.correlation_id:
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            body=json.dumps(response).encode("utf-8"),
            properties=pika.BasicProperties(
                correlation_id=properties.correlation_id,
                content_type="application/json",
            )
        )

    ch.basic_ack(
        delivery_tag=method.delivery_tag
    )

def start_consumer():
    """Continuously connect to RabbitMQ and consume worker jobs.

    The function declares the durable job queue, limits unacknowledged work to
    one message with basic_qos(prefetch_count=1), and registers callback as the
    message handler. If the consumer exits because of an exception, it waits five
    seconds before attempting to reconnect. Connections are closed in finally."""
    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(CONNECTION_PARAMETERS)
            
            channel = connection.channel()
            channel.queue_declare(
                queue=JOB_QUEUE, 
                durable=True
            )
            
            channel.basic_qos(prefetch_count=1)

            print("Connected to RabbitMQ")

            channel.basic_consume(
                queue=JOB_QUEUE,
                on_message_callback=callback,
            )
            
            channel.start_consuming()

        except Exception as e: # Reconnect on disconnect.
            print("RabbitMQ consumer stopped")
            print(e)
            time.sleep(5)

        finally:
            if connection is not None and connection.is_open:
                connection.close()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "4352"))
    start_consumer()