"""Адаптеры эмбеддингов (паттерн Adapter).

HashingEmbedder — детерминированный signed feature hashing без внешних
зависимостей (используется по умолчанию в dev/демо-режиме).
HuggingFaceEmbedder — настоящие sentence-transformers, включается через
EMBEDDING_BACKEND=hf.
"""
from __future__ import annotations

import abc
import hashlib
import math
import re

from app.core.config import Settings

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]+")


class BaseEmbedder(abc.ABC):
    dim: int

    @abc.abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


class HashingEmbedder(BaseEmbedder):
    """Дешёвая и стабильная альтернатива нейросетевым эмбеддерам."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            digest = hashlib.md5(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
            # bigram добавляет чуть контекста соседних слов
            index2 = int.from_bytes(digest[5:9], "big") % self.dim
            vector[index2] += sign * 0.5
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class HuggingFaceEmbedder(BaseEmbedder):
    def __init__(self, model_name: str, dim: int = 384) -> None:
        self.model_name = model_name
        self.dim = dim
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "Для EMBEDDING_BACKEND=hf установите sentence-transformers"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._ensure_model()
        vector = model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [[float(x) for x in vector] for vector in vectors]


def make_embedder(settings: Settings) -> BaseEmbedder:
    if settings.embedding_backend == "hf":
        return HuggingFaceEmbedder(settings.embedding_model, settings.embedding_dim)
    return HashingEmbedder(dim=settings.embedding_dim)
