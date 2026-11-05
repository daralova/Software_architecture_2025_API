from abc import ABC, abstractmethod
import numpy as np

class Segmenter(ABC):
    """Единый интерфейс всех сегментаторов (Strategy)."""

    @abstractmethod
    def segment(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Маска классов: H x W, 0 = фон, 1 = car, 2 = bus, 3 = truck."""

    @abstractmethod
    def classes(self) -> list[str]:
        ...
