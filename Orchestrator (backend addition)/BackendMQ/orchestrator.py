from flask import Flask, jsonify, request
import pika
from config import *
import json
import time
import uuid



app = Flask(__name__)
REPLY_TIMEOUT_SECONDS = 60

def send_and_recieve_job(job: dict):
    correlation_id = str(uuid.uuid4())
    response = None

    connection = pika.BlockingConnection(CONNECTION_PARAMETERS)
    try:
        channel = connection.channel()
        # set the job channel and reply channel
        channel.queue_declare(queue=JOB_QUEUE, durable=True)
        reply_queue = channel.queue_declare(queue="", exclusive=True, auto_delete=True).method.queue

        # I hate nesting functions but I could not for the life of me figure out how not to.
        def on_response(ch, method, properties, body):
            nonlocal response
            if properties.correlation_id == correlation_id:
                response = json.loads(body)

        # IF there is data in the reply queue, instantly consume it (because the model server may have already replied before we started waiting)
        channel.basic_consume(
            queue=reply_queue, 
            on_message_callback=on_response, 
            auto_ack=True
        ) 
        channel.confirm_delivery()
        
        channel.basic_publish(
            exchange="",
            routing_key=JOB_QUEUE,
            body=json.dumps(job).encode("utf-8"),
            properties=pika.BasicProperties(
                reply_to=reply_queue,
                correlation_id=correlation_id,
                delivery_mode=2,
                content_type="application/json",
            ),
            mandatory=True,
        )

        deadline = time.perf_counter() + REPLY_TIMEOUT_SECONDS # basically until timeout check every 0.2 seconds if the model server has replied yet
        while response is None and time.perf_counter() < deadline:
            connection.process_data_events(time_limit=0.2) # type: ignore

        if response is None:
            raise TimeoutError("No model server replied before the timeout.")
        if "error" in response:
            raise ValueError(response["error"])
        
        return response["result"]
    
    finally:
        if connection.is_open:
            connection.close()

@app.post("/api/predict")
def api_predict():
    
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json."
        }), 400

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400
        
    if not all(isinstance(x[0], str) and isinstance(x[1], str) for x in payload.items()):
        return jsonify({
            "error": "All keys and values in the JSON object must be strings."
        }), 418
        
    if len(payload) > MAX_REQUEST_LENGTH:
        return jsonify({
            "error": f"Request body must contain at most {MAX_REQUEST_LENGTH} texts."
        }), 413
        
    if not payload:
        return jsonify({}), 200
    
    try:
        return jsonify(
            send_and_recieve_job({
                "task": "predict", 
                "payload": payload
            })), 200
        
    except TimeoutError as error:
        return jsonify({
            "error": str(error)
        }), 504
    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 500
    except (pika.exceptions.AMQPError, OSError) as error: # type: ignore
        return jsonify({
            "error": "The job queue is unavailable."
        }), 503

@app.post("/api/reclassify")
def api_reclassify():
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json."
        }), 400

    payload = request.get_json(silent=True)
    
    if not isinstance(payload, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    text = payload.get("text") #so this one is for text
    flag = payload.get("flag") #this one is for 0 or 1 depending on user input
    
    if not isinstance(text, str) or not (isinstance(flag, bool) or (isinstance(flag, int) and flag in (0, 1))): #I don't know if this should be and or or, like I don't think any of them can be wrong, so and seems fine but idk kept or for now
        return jsonify({
            "error": "Request body must contain 'text' (string) and 'flag' (boolean)."
        }), 418

    try:
        return jsonify(send_and_recieve_job({
            "task": "reclassify", 
            "payload": {
                "text": text, 
                "flag": flag
            }
        })), 200
    
    except TimeoutError as error:
        return jsonify({
            "error": str(error)
        }), 504
    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 500
    except (pika.exceptions.AMQPError, OSError) as error: # type: ignore
        return jsonify({
            "error": "The job queue is unavailable."
        }), 503
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4351, threaded=True, debug=False)
