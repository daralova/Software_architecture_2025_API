"""Загружает встроенную базу знаний в хранилище и переиндексирует её.

Запуск: python scripts/seed_legal_knowledge.py
Требует настроенный backend (БД/pgvector/ES — по переменным окружения).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings  # noqa: E402
from app.facade.container import build_facade  # noqa: E402


def main() -> None:
    settings = get_settings()
    facade = build_facade(settings)
    count = facade.reindex()
    print(f"База знаний переиндексирована: {count} чанков")
    print(f"backends: storage={settings.storage_backend}, "
          f"vector={settings.vector_backend}, search={settings.search_backend}")


if __name__ == "__main__":
    main()
