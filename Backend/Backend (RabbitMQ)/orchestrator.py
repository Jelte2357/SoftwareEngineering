"""Flask HTTP API and RabbitMQ request-response orchestrator.

The API accepts prediction and reclassification requests, validates their
JSON payloads, publishes jobs to the configured RabbitMQ queue, and waits for
the worker response on a temporary exclusive reply queue. The Flask service
runs on port 4352 when this module is executed directly."""
import json
import pika
import time
import uuid

from config import *
from flask import Flask, jsonify, request

app = Flask(__name__)
REPLY_TIMEOUT_SECONDS = 60

def send_and_recieve_job(job: dict):
    """Publish a job and wait for the matching RabbitMQ response.

    Args:
        job: JSON-serializable job dictionary containing a task and payload.

    Returns:
        The ``result`` value from the worker's response message.

    Raises:
        TimeoutError: If no matching response arrives before the configured
            reply timeout.
        ValueError: If the worker response contains an ``error`` field.
        pika.exceptions.AMQPError or OSError: If RabbitMQ communication fails.

    Notes:
        A UUID correlation ID associates the response with this request. A
        temporary exclusive auto-delete reply queue is created for the request."""
    correlation_id = str(uuid.uuid4())
    response = None

    connection = pika.BlockingConnection(CONNECTION_PARAMETERS)
    try:
        channel = connection.channel()
        # set the job channel and reply channel
        channel.queue_declare(queue=JOB_QUEUE, durable=True)
        reply_queue = channel.queue_declare(queue="", exclusive=True, auto_delete=True).method.queue

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
    
    """Validate and submit a batch of texts for prediction.

    Accepts a JSON object whose string keys identify input texts and whose
    string values contain the text to classify. The job is sent to the worker
    through RabbitMQ and the worker result is returned as JSON.

    Returns:
        Flask JSON response with HTTP 200 on success, or an error response using
        the status codes selected by the validation/exception branches."""
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
    """Validate and submit a user reclassification record.

    Expects a JSON object containing a string ``text`` and a boolean-like
    ``flag`` (a bool or integer 0/1). The request is forwarded to the worker as a
    ``reclassify`` task; this endpoint records feedback rather than retraining.

    Returns:
        Flask JSON response containing the worker result, or an error response
        using the status codes selected by the validation/exception branches."""
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
    app.run(host="0.0.0.0", port=4352, threaded=True, debug=False)
