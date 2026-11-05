"""Telemetry collector: Observer -> Kafka producer.

Подписывается на EventBus симуляции и публикует каждое событие в Kafka-топик.
Если Kafka недоступна (или библиотека не установлена), коллектор деградирует
в no-op: обучение не ломается.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

log = logging.getLogger(__name__)


class TelemetryCollector:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        kafka_cfg = cfg.get("kafka", {})
        self.topic = kafka_cfg.get("topic", "dungeon-telemetry")
        self.enabled = bool(kafka_cfg.get("enabled", False))
        self._producer = None
        self._sent = 0
        if self.enabled:
            try:
                from kafka import KafkaProducer
                self._producer = KafkaProducer(
                    bootstrap_servers=kafka_cfg.get("bootstrap_servers", "localhost:9092"),
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    linger_ms=20,
                )
                log.info("Kafka producer подключен: %s", kafka_cfg.get("bootstrap_servers"))
            except Exception as exc:
                log.warning("Kafka недоступна (%s) - телеметрия отключена", exc)
                self.enabled = False

    def send(self, event: Any) -> None:
        if self._producer is None:
            return
        try:
            self._producer.send(self.topic, event.to_dict())
            self._sent += 1
        except Exception as exc:
            log.warning("Не удалось отправить событие в Kafka: %s", exc)

    def flush(self) -> None:
        if self._producer is not None:
            self._producer.flush()

    def close(self) -> None:
        if self._producer is not None:
            self._producer.flush()
            self._producer.close()
            print(f"[telemetry] отправлено событий: {self._sent}")
