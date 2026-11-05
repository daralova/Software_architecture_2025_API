"""Object analytics: из пиксельной маски достаём объекты (контуры, центроиды,
bbox, площадь), оцениваем скорость (Strategy), публикуем события в Kafka."""
import math
import uuid
import cv2
import numpy as np
from app.pipeline.base import Stage, FrameContext
from app.adapters.minio_adapter import ObjectStorage
from app.adapters.kafka_adapter import KafkaEventProducer
from app.core.config import settings


class SpeedEstimator:
    """Strategy: разные способы оценки скорости. Базовая реализация — эмпирика
    через площадь маски; в проде заменяется на трекинг между кадрами."""

    def estimate(self, area_px: int, frame_w: int) -> float | None:
        ratio = area_px / (frame_w * 360.0)   # нормировка на высоту кадра 360p
        if ratio <= 0:
            return None
        return round(min(120.0, 8.0 * math.sqrt(ratio) * 10.0), 1)


class AreaSpeedEstimator(SpeedEstimator):
    pass


class ObjectAnalyticsStage(Stage):
    name = "analytics"

    def __init__(self, storage: ObjectStorage | None = None,
                 producer: KafkaEventProducer | None = None,
                 speed_strategy: SpeedEstimator | None = None):
        self.storage = storage
        self.producer = producer
        self.speed = speed_strategy or AreaSpeedEstimator()

    def process(self, ctx: FrameContext) -> FrameContext:
        frame_key = ""
        if self.storage is not None:
            frame_key = self.storage.put_image(
                f"frames/{ctx.camera_id}/{uuid.uuid4().hex}.jpg", ctx.image)
        ctx.storage_keys["frame_key"] = frame_key

        w = ctx.mask.shape[1]
        for class_idx, class_name in enumerate(settings.classes, start=1):
            layer = (ctx.mask == class_idx).astype(np.uint8)
            if layer.sum() == 0:
                continue
            contours, _ = cv2.findContours(layer, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = int(cv2.contourArea(cnt))
                if area < settings.min_blob_area:
                    continue
                x, y, cw, ch = cv2.boundingRect(cnt)
                event = {
                    "camera_id": ctx.camera_id,
                    "frame_index": ctx.frame_index,
                    "frame_key": frame_key,
                    "mask_key": ctx.storage_keys.get("mask_key"),
                    "class_name": class_name,
                    "pixel_area": area,
                    "centroid": [round(x + cw / 2, 1), round(y + ch / 2, 1)],
                    "bbox": [x, y, x + cw, y + ch],
                    "speed_kmh": self.speed.estimate(area, w),
                }
                ctx.events.append(event)
                if self.producer:
                    self.producer.publish(event)
        return ctx
