
import pika

# RabbitMQ connection credentials
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

# Declare the queues
channel.queue_declare(queue="interface_requests", durable=True)
channel.queue_declare(queue="ai_requests", durable=True)

# Enable publisher confirms
channel.confirm_delivery()

# Only process one message at a time
channel.basic_qos(prefetch_count=1)

print("Orchestrator is running...")
print("Waiting for incoming requests...")



def forward_request(ch, method, properties, body):

    print("\nReceived a request from the interface.")

    try:
        # Forward the request to the AI queue
        ch.basic_publish(
            exchange="",
            routing_key="ai_requests",
            body=body,
            properties=pika.BasicProperties(
                reply_to=properties.reply_to,
                correlation_id=properties.correlation_id,
                delivery_mode=2,
                content_type="application/json"
            ),
            mandatory=True
        )

        # This point is reached only after RabbitMQ confirms
        # that the message has been accepted.
        print("RabbitMQ confirmed the message.")

        # Acknowledge the original message
        ch.basic_ack(delivery_tag=method.delivery_tag)

        print("Original request acknowledged.")

    except (pika.exceptions.NackError,
            pika.exceptions.UnroutableError) as error:

        print(f"Message was not confirmed: {error}")

        # Return the original message to the queue
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True
        )



# Listen for incoming interface requests
channel.basic_consume(
    queue="interface_requests",
    on_message_callback=forward_request
)

channel.start_consuming()
