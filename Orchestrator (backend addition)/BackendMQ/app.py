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
    keys, texts = zip(*payload.items())
    texts = cast(tuple[str], tuple(map(normalize.normalize_all_apply, texts)))
    predictions = predict_texts(texts)
    results = dict(zip(keys, predictions))
    return results

def reclassify(payload: dict) -> dict:
    text = payload["text"]
    flag = bool(payload["flag"])
    
    text_hash = hashlib.blake2b(text.encode("utf-8")).hexdigest()
    
    with db.lock:
        db.insert_flag(text_hash, flag) #I don't know if we need to change the insert_flag function at all, I am not really an expert in conn.execute()
    
    return {"hash": text_hash, "flag": payload["flag"], "message": "saved"}

def callback(ch, method, properties, body):
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

# def process_queue_job(job: dict):
#     task = job.get("task")
#     payload = job.get("payload")
    
#     # 2 very simple checks because otherwise my static type checker gets mad at me
#     assert isinstance(payload, dict), ValueError("Job payload must be a dictionary.")
#     assert isinstance(task, str) and task in {"predict", "reclassify"}, ValueError("Job task must be 'predict' or 'reclassify'.")
    
#     if task == "predict":
#         return predict(payload)
#     elif task == "reclassify":
#         return reclassify(payload)

# def start_consumer():
#     while True:
#         connection = None
#         try:
#             connection = pika.BlockingConnection(CONNECTION_PARAMETERS)
#             channel = connection.channel()
#             channel.queue_declare(queue=JOB_QUEUE, durable=True)
#             channel.basic_qos(prefetch_count=1)
            
#             print("Connected to RabbitMQ")

#             for method, properties, body in channel.consume(queue=JOB_QUEUE, auto_ack=False):
#                 if method is None or properties is None or body is None:
#                     raise RuntimeError("RabbitMQ returned incomplete delivery metadata.")

#                 job_id = properties.correlation_id
#                 started = time.perf_counter()
#                 try:
#                     job = json.loads(body) #.decode("utf-8"))
#                     response = {"result": process_queue_job(job)}
#                     print(job_id, time.perf_counter() - started)
                    
#                 except Exception as e:
#                     response = {"error": str(e)}

#                 if properties.reply_to and properties.correlation_id:
#                     channel.basic_publish(
#                         exchange="",
#                         routing_key=properties.reply_to,
#                         properties=pika.BasicProperties(
#                             correlation_id=properties.correlation_id,
#                             content_type="application/json",
#                         ),
#                         body=json.dumps(response).encode("utf-8"),
#                     )

#                 channel.basic_ack(delivery_tag=method.delivery_tag)
                
#         except Exception as e:
#             print("RabbitMQ consumer stopped")
#             print(e)
#             time.sleep(5)
        
#         finally:
#             if connection is not None and connection.is_open:
#                 connection.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "4352"))
    start_consumer()