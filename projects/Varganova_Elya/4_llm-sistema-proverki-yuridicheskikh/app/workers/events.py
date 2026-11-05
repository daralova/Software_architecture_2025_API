"""Событийная шина (паттерн Adapter): Kafka / in-memory."""
from __future__ import annotations

import abc
import json
import queue
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class Event:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "payload": self.payload}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "Event":
        data = json.loads(raw)
        return cls(type=data["type"], payload=data.get("payload", {}), id=data.get("id", ""))


class EventBus(abc.ABC):
    @abc.abstractmethod
    def publish(self, event: Event) -> None: ...

    @abc.abstractmethod
    def stream(self, timeout: float | None = 1.0) -> Iterator[Event]: ...


class InMemoryEventBus(EventBus):
    """Очередь в памяти: для dev-режима и запуска демо без Kafka."""

    def __init__(self, maxsize: int = 10_000) -> None:
        self._queue: queue.Queue[Event] = queue.Queue(maxsize=maxsize)

    def publish(self, event: Event) -> None:
        self._queue.put(event)

    def stream(self, timeout: float | None = 1.0) -> Iterator[Event]:
        while True:
            try:
                yield self._queue.get(timeout=timeout)
            except queue.Empty:
                continue


class KafkaEventBus(EventBus):
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str) -> None:
        self._bootstrap = bootstrap_servers
        self._topic = topic
        self._group = group_id

    def _producer(self):
        try:
            from kafka import KafkaProducer
        except ImportError as exc:
            raise RuntimeError("Для Kafka установите пакет kafka-python-ng") from exc
        return KafkaProducer(
            bootstrap_servers=self._bootstrap,
            value_serializer=lambda value: value.encode("utf-8"),
        )

    def publish(self, event: Event) -> None:
        producer = self._producer()
        try:
            producer.send(self._topic, event.to_json())
            producer.flush()
        finally:
            producer.close()

    def stream(self, timeout: float | None = 1.0) -> Iterator[Event]:
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:
            raise RuntimeError("Для Kafka установите пакет kafka-python-ng") from exc
        consumer = KafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap,
            group_id=self._group,
            value_deserializer=lambda value: value.decode("utf-8"),
        )
        try:
            for message in consumer:
                yield Event.from_json(message.value)
        finally:
            consumer.close()


def make_event_bus(settings) -> EventBus:
    if settings.bus_backend == "kafka":
        return KafkaEventBus(
            settings.kafka_bootstrap_servers,
            settings.kafka_topic,
            settings.kafka_consumer_group,
        )
    return InMemoryEventBus()
