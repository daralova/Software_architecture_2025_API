"""Adapter вокруг kafka-python: продюсер и консюмер с единым интерфейсом."""
import json
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("kafka")

class KafkaEventProducer:
    def __init__(self):
        self._producer = None

    def _ensure(self):
        if self._producer is None:
            from kafka import KafkaProducer
            self._producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode(),
            )
        return self._producer

    def publish(self, event: dict):
        try:
            self._ensure().send(settings.kafka_topic, value=event)
        except Exception as e:
            log.warning("Kafka send failed: %s", e)

    def close(self):
        if self._producer:
            self._producer.close()


class KafkaEventConsumer:
    def __init__(self, group: str = "traffic-analytics"):
        from kafka import KafkaConsumer
        self.consumer = KafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=settings.kafka_bootstrap,
            group_id=group,
            value_deserializer=lambda v: json.loads(v.decode()),
            auto_offset_reset="latest",
        )

    def events(self):
        for msg in self.consumer:
            yield msg.value
