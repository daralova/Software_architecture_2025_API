"""Adapter: приводим модель из Hugging Face (SegFormer) к интерфейсу Segmenter."""
import numpy as np
import torch
import cv2
from app.models.base import Segmenter
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("segformer")

class SegFormerAdapter(Segmenter):
    """Оборачивает pretrained SegFormer так, что снаружи видна маска с индексами
    1 = car, 2 = bus, 3 = truck. Подмена модели не затрагивает пайплайн."""

    def __init__(self, model_id: str = "nvidia/segformer-b0-finetuned-cityscapes-1024-1024",
                 device: str | None = None):
        try:
            from transformers import SegformerForSemanticSegmentation
        except ImportError as e:
            raise RuntimeError("pip install transformers") from e
        self.device = device or settings.device
        self.model = SegformerForSemanticSegmentation.from_pretrained(model_id).to(self.device)
        self.processor_model_id = model_id
        # Cityscapes trainId: car=13, bus=0/6, truck=8
        self.city_to_local = {13: 1, 0: 2, 6: 2, 8: 3}
        self.model.eval()

    def segment(self, frame_bgr: np.ndarray) -> np.ndarray:
        from transformers import SegformerImageProcessor
        proc = SegformerImageProcessor.from_pretrained(self.processor_model_id)
        img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        inputs = proc(images=img, return_tensors="pt").to(self.device)
        with torch.no_grad():
            logits = self.model(**inputs).logits
            logits = torch.nn.functional.interpolate(
                logits, size=img.shape[:2], mode="bilinear", align_corners=False)
            ids = logits.argmax(dim=1).squeeze(0).cpu().numpy()
        local = np.zeros_like(ids, dtype=np.uint8)
        for city_id, local_id in self.city_to_local.items():
            local[ids == city_id] = local_id
        return local

    def classes(self) -> list[str]:
        return ["background", *settings.classes]
