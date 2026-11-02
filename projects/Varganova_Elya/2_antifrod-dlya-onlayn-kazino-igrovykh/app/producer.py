from kafka import KafkaProducer
import json

producer = KafkaProducer(bootstrap_servers=["kafka:29092"], value_serializer=lambda v: json.dumps(v).encode('utf-8'))

def send_event(topic: str, event: dict):
    producer.send(topic, value=event)
    producer.flush()
