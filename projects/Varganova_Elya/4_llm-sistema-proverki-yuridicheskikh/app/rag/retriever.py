"""Гибридный ретривер: плотный (векторный) + разреженный (лексический) поиск.

Слияние результатов — через Reciprocal Rank Fusion (RRF).
"""
from __future__ import annotations

from typing import Any

from app.adapters.embeddings import BaseEmbedder
from app.adapters.search import BaseSearchClient
from app.adapters.vector_store import BaseVectorStore
from app.domain.entities import KnowledgeChunk

RRF_K = 60


class HybridRetriever:
    def __init__(
        self,
        embedder: BaseEmbedder,
        vector_store: BaseVectorStore,
        search_client: BaseSearchClient,
        top_k: int = 3,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._search = search_client
        self._top_k = top_k
        self._chunks: dict[str, KnowledgeChunk] = {}

    def index(self, chunks: list[KnowledgeChunk]) -> int:
        """Индексирует чанки знаний в оба индекса. Возвращает количество."""
        self._chunks = {chunk.id: chunk for chunk in chunks}
        vectors = self._embedder.embed_batch([chunk.content for chunk in chunks])
        for chunk, vector in zip(chunks, vectors):
            metadata = {"title": chunk.title, "source": chunk.source, "content": chunk.content}
            self._vector_store.upsert(chunk.id, vector, metadata)
            self._search.index(chunk.id, f"{chunk.title} {chunk.content}", metadata)
        return len(chunks)

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        limit = top_k or self._top_k
        query_vector = self._embedder.embed(query)
        dense = self._vector_store.search(query_vector, top_k=limit)
        sparse = self._search.search(query, top_k=limit)

        fused: dict[str, float] = {}
        for rank, (chunk_id, _, _) in enumerate(dense):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, (chunk_id, _, _) in enumerate(sparse):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)

        results = sorted(fused.items(), key=lambda item: item[1], reverse=True)
        citations = []
        for chunk_id, score in results[:limit]:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                continue
            citations.append({
                "chunk_id": chunk.id,
                "title": chunk.title,
                "source": chunk.source,
                "snippet": " ".join(chunk.content.split())[:180],
                "score": round(score, 6),
            })
        return citations
