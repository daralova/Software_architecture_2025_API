"""Segmentation inference: прогон кадра через сегментатор (Strategy) и
сохранение маски в MinIO (Adapter)."""
import uuid
from app.pipeline.base import Stage, FrameContext
from app.models import create_segmenter
from app.adapters.minio_adapter import ObjectStorage
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("segmentation")

class SegmentationStage(Stage):
    name = "segmentation"

    def __init__(self, model_name: str | None = None,
                 storage: ObjectStorage | None = None):
        self.segmenter = create_segmenter(model_name)
        self.storage = storage
        log.info("Модель: %s, классы: %s", model_name or settings.model_name,
                 self.segmenter.classes())

    def process(self, ctx: FrameContext) -> FrameContext:
        mask = self.segmenter.segment(ctx.image)
        ctx.mask = mask
        if self.storage is not None:
            key = f"masks/{ctx.camera_id}/{uuid.uuid4().hex}.png"
            ctx.storage_keys["mask_key"] = self.storage.put_image(key, mask * 80)
        return ctx
