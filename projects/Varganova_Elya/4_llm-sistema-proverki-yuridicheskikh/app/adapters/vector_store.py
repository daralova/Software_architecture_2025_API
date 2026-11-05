"""Адаптеры векторного индекса (паттерн Adapter): pgvector / in-memory."""
from __future__ import annotations

import abc
import json
import math
from typing import Any


class BaseVectorStore(abc.ABC):
    @abc.abstractmethod
    def upsert(self, chunk_id: str, vector: list[float], metadata: dict[str, Any]) -> None: ...

    @abc.abstractmethod
    def search(self, vector: list[float], top_k: int = 3) -> list[tuple[str, float, dict[str, Any]]]: ...


class InMemoryVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        self._vectors: dict[str, tuple[list[float], dict[str, Any]]] = {}

    def upsert(self, chunk_id, vector, metadata) -> None:
        self._vectors[chunk_id] = (vector, metadata)

    def search(self, vector, top_k=3):
        scored = []
        for chunk_id, (other, metadata) in self._vectors.items():
            score = _cosine(vector, other)
            scored.append((chunk_id, score, metadata))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class PgVectorStore(BaseVectorStore):
    """Хранит эмбеддинги в колонке vector(384) (см. db/init.sql).

    Заполнение содержимого чанка выполняет репозиторий знаний; здесь мы
    поддерживаем вектор в актуальном состоянии и ищем по косинусной дистанции.
    """

    def __init__(self, engine) -> None:
        self._engine = engine

    def upsert(self, chunk_id, vector, metadata) -> None:
        from sqlalchemy import text as sql_text

        stmt = sql_text(
            """
            INSERT INTO knowledge_chunks (id, title, source, content, embedding)
            VALUES (:id, :title, :source, :content, CAST(:embedding AS vector))
            ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding
            """
        )
        with self._engine.begin() as conn:
            conn.execute(stmt, {
                "id": chunk_id,
                "title": metadata.get("title", ""),
                "source": metadata.get("source", ""),
                "content": metadata.get("content", ""),
                "embedding": "[" + ",".join(f"{x:.6f}" for x in vector) + "]",
            })

    def search(self, vector, top_k=3):
        from sqlalchemy import text as sql_text

        stmt = sql_text(
            """
            SELECT id, 1 - (embedding <=> CAST(:embedding AS vector)) AS score,
                   title, source, content
            FROM knowledge_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )
        params = {
            "embedding": "[" + ",".join(f"{x:.6f}" for x in vector) + "]",
            "limit": top_k,
        }
        with self._engine.begin() as conn:
            rows = conn.execute(stmt, params).mappings().all()
        return [
            (
                row["id"],
                float(row["score"]),
                {"title": row["title"], "source": row["source"], "content": row["content"]},
            )
            for row in rows
        ]


def make_vector_store(settings, engine=None) -> BaseVectorStore:
    if settings.vector_backend == "pgvector":
        if engine is None:
            raise ValueError("Для pgvector нужен SQLAlchemy engine")
        return PgVectorStore(engine)
    return InMemoryVectorStore()
