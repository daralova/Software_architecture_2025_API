from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import numpy as np

@dataclass
class FrameContext:
    """Данные, которые проходят через стадии пайплайна."""
    camera_id: int
    frame_index: int
    image: np.ndarray | None = None
    mask: np.ndarray | None = None
    detections: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    storage_keys: dict = field(default_factory=dict)


class Stage(ABC):
    """Одна стадия Pipeline-паттерна."""

    name: str = "stage"

    @abstractmethod
    def process(self, ctx: FrameContext) -> FrameContext:
        ...
