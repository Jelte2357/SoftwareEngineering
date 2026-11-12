
import pika
import json
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

# --------------------------------------------------
# LOAD THE LOCAL DISTILBERT MODEL
# --------------------------------------------------

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "distilbert_classifier"
)

print("Loading DistilBERT model...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)

model.eval()

print("DistilBERT model loaded successfully!")

# --------------------------------------------------
# RABBITMQ CONNECTION
# --------------------------------------------------

credentials = pika.PlainCredentials(
    "se_user",
    "dev_only_change_this"
)

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5672,
        credentials=credentials
    )
)

channel = connection.channel()

channel.queue_declare(
    queue="ai_requests",
    durable=True
)

channel.basic_qos(prefetch_count=1)

print("Waiting for requests...")


# --------------------------------------------------
# CLASSIFICATION FUNCTION
# --------------------------------------------------

def classify_text(text):

    # Convert text into tokens that DistilBERT understands
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    # Run the model without calculating gradients
    with torch.no_grad():
        outputs = model(**inputs)

    # Convert raw model outputs into probabilities
    probabilities = torch.softmax(
        outputs.logits,
        dim=-1
    )

    # Find the class with the highest probability
    predicted_class = torch.argmax(
        probabilities,
        dim=-1
    ).item()

    # Get the confidence of the prediction
    confidence = probabilities[0][predicted_class].item()

    # Interpret the predicted class
    if predicted_class == 0:
        classification = "Not hate speech"
    else:
        classification = "Hate speech"

    return {
        "predicted_class": predicted_class,
        "classification": classification,
        "confidence": round(confidence, 4)
    }


# --------------------------------------------------
# RABBITMQ CALLBACK
# --------------------------------------------------

def callback(ch, method, properties, body):

    print("\nReceived a request!")

    try:
        # Decode incoming JSON
        message = json.loads(body.decode())

        request_id = message["request_id"]
        text = message["text"]

        print(f"Request ID: {request_id}")
        print(f"Text: {text}")

        # Run the actual AI classification
        result = classify_text(text)

        print(f"Prediction: {result['classification']}")
        print(f"Confidence: {result['confidence']}")

        # Prepare the response
        response = {
            "request_id": request_id,
            "status": "success",
            "original_text": text,
            "predicted_class": result["predicted_class"],
            "classification": result["classification"],
            "confidence": result["confidence"]
        }

    except Exception as error:

        print(f"An error occurred: {error}")

        response = {
            "status": "error",
            "error": str(error)
        }

    # Send response back to the producer
    ch.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        body=json.dumps(response),
        properties=pika.BasicProperties(
            correlation_id=properties.correlation_id,
            content_type="application/json"
        )
    )

    print("Response sent!")

    # Acknowledge the original request
    ch.basic_ack(
        delivery_tag=method.delivery_tag
    )


# --------------------------------------------------
# START CONSUMING
# --------------------------------------------------

channel.basic_consume(
    queue="ai_requests",
    on_message_callback=callback
)

channel.start_consuming()

