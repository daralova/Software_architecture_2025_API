"""Адаптеры объектного хранилища (паттерн Adapter): MinIO / in-memory."""
from __future__ import annotations

import abc
import io

from app.core.config import Settings


class BaseObjectStorage(abc.ABC):
    @abc.abstractmethod
    def put(self, key: str, data: bytes) -> None: ...

    @abc.abstractmethod
    def get(self, key: str) -> bytes: ...


class InMemoryStorage(BaseObjectStorage):
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> None:
        self._objects[key] = data

    def get(self, key: str) -> bytes:
        if key not in self._objects:
            raise KeyError(f"Объект {key!r} не найден в хранилище")
        return self._objects[key]


class MinIOStorage(BaseObjectStorage):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                from minio import Minio
            except ImportError as exc:
                raise RuntimeError(
                    "Для STORAGE_BACKEND=minio установите пакет minio"
                ) from exc
            self._client = Minio(
                self._settings.minio_endpoint,
                access_key=self._settings.minio_access_key,
                secret_key=self._settings.minio_secret_key,
                secure=self._settings.minio_endpoint.startswith("https"),
            )
            bucket = self._settings.minio_bucket
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
        return self._client

    def put(self, key: str, data: bytes) -> None:
        client = self._ensure_client()
        client.put_object(
            self._settings.minio_bucket, key, io.BytesIO(data), length=len(data)
        )

    def get(self, key: str) -> bytes:
        client = self._ensure_client()
        response = client.get_object(self._settings.minio_bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


def make_storage(settings: Settings):
    if settings.storage_backend == "minio":
        return MinIOStorage(settings)
    return InMemoryStorage()
