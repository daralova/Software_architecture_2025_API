"""Фабрики SQLAlchemy engine/session. Тяжёлые импорты — ленивые."""
from __future__ import annotations

from typing import Any

from app.core.config import Settings


def get_engine(settings: Settings) -> Any:
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "SQLAlchemy не установлен. Установите зависимости из requirements.txt"
        ) from exc
    return create_engine(settings.database_url, echo=settings.database_echo)


def make_session_factory(engine: Any) -> Any:
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
