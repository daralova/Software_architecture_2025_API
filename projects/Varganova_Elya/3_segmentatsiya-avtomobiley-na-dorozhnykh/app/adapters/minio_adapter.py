"""Adapter над MinIO (S3-совместимое хранилище) для кадров и масок."""
import io
import numpy as np
import cv2
from minio import Minio
from app.core.config import settings

class ObjectStorage:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
        if not self.client.bucket_exists(settings.minio_bucket):
            self.client.make_bucket(settings.minio_bucket)

    def put_image(self, key: str, image: np.ndarray) -> str:
        ok, buf = cv2.imencode(".jpg", image)
        if not ok:
            raise ValueError("Не удалось закодировать изображение")
        data = buf.tobytes()
        self.client.put_object(
            settings.minio_bucket, key, io.BytesIO(data), len(data),
            content_type="image/jpeg")
        return key

    def get_image(self, key: str) -> np.ndarray | None:
        try:
            resp = self.client.get_object(settings.minio_bucket, key)
            arr = np.frombuffer(resp.read(), dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception:
            return None

    def presigned_url(self, key: str, hours: int = 1) -> str:
        from datetime import timedelta
        return self.client.presigned_get_object(
            settings.minio_bucket, key, expires=timedelta(hours=hours))
