"""Конфигурация приложения.

Если установлен pydantic-settings — используем его (валидация, .env).
Иначе работает упрощённый fallback на dataclass + os.environ: это позволяет
запускать демо и тесты без установки зависимостей.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Settings:
    app_name: str = "contract-review-llm"
    environment: str = _env("ENVIRONMENT", "dev")
    log_level: str = _env("LOG_LEVEL", "INFO")

    database_url: str = _env("DATABASE_URL", "postgresql+psycopg2://cr:cr@localhost:5432/contracts")
    database_echo: bool = _env("DATABASE_ECHO", "false").lower() == "true"

    storage_backend: str = _env("STORAGE_BACKEND", "memory")          # memory | minio
    minio_endpoint: str = _env("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = _env("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = _env("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = _env("MINIO_BUCKET", "contracts")

    vector_backend: str = _env("VECTOR_BACKEND", "memory")            # memory | pgvector
    search_backend: str = _env("SEARCH_BACKEND", "memory")            # memory | elasticsearch
    elasticsearch_url: str = _env("ELASTICSEARCH_URL", "http://localhost:9200")
    elasticsearch_index: str = _env("ELASTICSEARCH_INDEX", "legal_knowledge")

    embedding_backend: str = _env("EMBEDDING_BACKEND", "hashing")     # hashing | hf
    embedding_model: str = _env("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    embedding_dim: int = int(_env("EMBEDDING_DIM", "384"))

    llm_backend: str = _env("LLM_BACKEND", "rule-based")              # rule-based | hf
    llm_model: str = _env("LLM_MODEL", "google/flan-t5-base")

    bus_backend: str = _env("BUS_BACKEND", "memory")                  # memory | kafka
    kafka_bootstrap_servers: str = _env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic: str = _env("KAFKA_TOPIC", "contract-events")
    kafka_consumer_group: str = _env("KAFKA_CONSUMER_GROUP", "contract-review-worker")

    rag_top_k: int = int(_env("RAG_TOP_K", "3"))

    def __post_init__(self) -> None:
        """Позволяет переопределять поля через одноимённые переменные окружения."""
        for f in fields(self):
            env_value = os.environ.get(f.name.upper())
            if env_value is None:
                continue
            current = getattr(self, f.name)
            if isinstance(current, bool):
                setattr(self, f.name, env_value.lower() == "true")
            elif isinstance(current, int):
                setattr(self, f.name, int(env_value))
            else:
                setattr(self, f.name, env_value)


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
