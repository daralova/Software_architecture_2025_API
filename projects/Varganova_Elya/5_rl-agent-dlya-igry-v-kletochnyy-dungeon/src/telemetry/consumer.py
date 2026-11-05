"""Консьюмер телеметрии: агрегирует поток событий и печатает сводку.

Запуск:
    python -m src.telemetry.consumer --bootstrap localhost:9092
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="dungeon-telemetry")
    parser.add_argument("--group", default="dungeon-aggregator")
    args = parser.parse_args()

    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=args.bootstrap,
        group_id=args.group,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
    )
    counts: Counter = Counter()
    window_start = time.time()
    print(f"[consumer] слушаю топик {args.topic!r} ... Ctrl+C для выхода")
    try:
        for message in consumer:
            event = message.value
            counts[event["type"]] += 1
            if time.time() - window_start >= 10:
                print("[consumer] события за 10с:", dict(counts))
                counts.clear()
                window_start = time.time()
    except KeyboardInterrupt:
        print("[consumer] остановлен")


if __name__ == "__main__":
    main()
