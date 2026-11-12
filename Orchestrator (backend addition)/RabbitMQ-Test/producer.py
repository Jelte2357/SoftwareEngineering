
import pika
import json
import uuid
import time

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
channel.queue_declare(queue="interface_requests", durable=True)

# Create a temporary queue for the response
result = channel.queue_declare(queue="", exclusive=True)
callback_queue = result.method.queue

# Store all received responses
responses = {}

# Store all requests that are still waiting for a response
pending_requests = {}

def on_response(ch, method, properties, body):

    correlation_id = properties.correlation_id

    # Check whether this response belongs to one of our requests
    if correlation_id in pending_requests:

        # Remove the request from the pending list
        request_id = pending_requests.pop(correlation_id)

        # Store the received response
        responses[correlation_id] = json.loads(body.decode())

        print(f"Received response for: {request_id}")
    
# Listen to the temporary reply queue
channel.basic_consume(
    queue=callback_queue,
    on_message_callback=on_response,
    auto_ack=True
)

# Create the request
# Create multiple requests
messages = [
    {
        "request_id": "1",
        "text": "I really dislike this person.",
        "language": "en"
    },
    {
        "request_id": "2",
        "text": "You are an idiot.",
        "language": "en"
    },
    {
        "request_id": "3",
        "text": "Have a wonderful day!",
        "language": "en"
    }
]

print("Sending requests...")

# Send every message
for message in messages:

    # Give each request its own unique correlation ID
    correlation_id = str(uuid.uuid4())

    # Keep track of which request this ID belongs to
    pending_requests[correlation_id] = message["request_id"]

    # Publish the request
    channel.basic_publish(
        exchange="",
        routing_key="interface_requests",
        body=json.dumps(message),
        properties=pika.BasicProperties(
            reply_to=callback_queue,
            correlation_id=correlation_id,
            delivery_mode=2
        )
    )

    print(f"Sent request {message['request_id']}")

print("\nWaiting for responses...")

# Wait for a maximum of 30 seconds
deadline = time.monotonic() + 30

while len(responses) < len(messages) and time.monotonic() < deadline:
    connection.process_data_events(time_limit=1)

# Display the responses we received
print("\nResults:")

for result in responses.values():
    print(json.dumps(result, indent=4))

# Report requests that did not receive a response
if pending_requests:
    print("\nThe following requests did not receive a response:")
    for request_id in pending_requests.values():
        print(request_id)
else:
    print("\nAll requests received a response!")

connection.close()
