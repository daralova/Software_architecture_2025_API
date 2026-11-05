"""Адаптеры полнотекстового поиска (паттерн Adapter): Elasticsearch / in-memory."""
from __future__ import annotations

import abc
import math
import re
from typing import Any

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)


class BaseSearchClient(abc.ABC):
    @abc.abstractmethod
    def index(self, doc_id: str, text: str, metadata: dict[str, Any]) -> None: ...

    @abc.abstractmethod
    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float, dict[str, Any]]]: ...


class InMemorySearchClient(BaseSearchClient):
    """Простейший TF-IDF-подобный поиск — замена ES в dev-режиме."""

    def __init__(self) -> None:
        self._docs: dict[str, tuple[list[str], dict[str, Any]]] = {}

    def index(self, doc_id, text, metadata) -> None:
        self._docs[doc_id] = (_TOKEN_RE.findall(text.lower()), metadata)

    def search(self, query, top_k=3):
        terms = set(_TOKEN_RE.findall(query.lower()))
        if not terms:
            return []
        df: dict[str, int] = {}
        for tokens, _ in self._docs.values():
            for term in set(tokens):
                if term in terms:
                    df[term] = df.get(term, 0) + 1
        scored = []
        n_docs = max(len(self._docs), 1)
        for doc_id, (tokens, metadata) in self._docs.items():
            score = 0.0
            for term in terms:
                tf = tokens.count(term)
                if tf == 0:
                    continue
                idf = math.log(1 + n_docs / (1 + df.get(term, 0)))
                score += tf * idf
            if score > 0:
                scored.append((doc_id, score, metadata))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class ElasticsearchSearchClient(BaseSearchClient):
    def __init__(self, url: str, index: str) -> None:
        self._url = url.rstrip("/")
        self._index = index
        self._session = None

    def _ensure_session(self):
        if self._session is None:
            try:
                import requests
            except ImportError as exc:
                raise RuntimeError("Для Elasticsearch нужен пакет requests") from exc
            self._session = requests.Session()
        return self._session

    def index(self, doc_id, text, metadata) -> None:
        session = self._ensure_session()
        response = session.put(
            f"{self._url}/{self._index}/_doc/{doc_id}",
            json={"text": text, **metadata},
            timeout=10,
        )
        response.raise_for_status()

    def search(self, query, top_k=3):
        session = self._ensure_session()
        response = session.post(
            f"{self._url}/{self._index}/_search",
            json={"size": top_k, "query": {"match": {"text": {"query": query}}}},
            timeout=10,
        )
        response.raise_for_status()
        hits = response.json().get("hits", {}).get("hits", [])
        return [
            (
                hit["_id"],
                float(hit.get("_score", 0.0)),
                {k: v for k, v in hit.get("_source", {}).items() if k != "text"},
            )
            for hit in hits
        ]


def make_search_client(settings) -> BaseSearchClient:
    if settings.search_backend == "elasticsearch":
        return ElasticsearchSearchClient(settings.elasticsearch_url, settings.elasticsearch_index)
    return InMemorySearchClient()
