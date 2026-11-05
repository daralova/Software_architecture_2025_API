"""Repository: абстракция доступа к хранилищу событий."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class EventRecord:
    camera_id: int
    frame_key: str
    mask_key: str
    class_name: str
    pixel_area: int
    centroid_x: float
    centroid_y: float
    bbox_x1: float
    bbox_y1: float
    bbox_x2: float
    bbox_y2: float
    speed_kmh: float | None = None
    created_at: datetime | None = None


class DetectionRepository(ABC):
    @abstractmethod
    def add_event(self, **kwargs) -> int:
        ...

    @abstractmethod
    def list_events(self, camera_id: int | None = None, class_name: str | None = None,
                    limit: int = 100) -> list[EventRecord]:
        ...

    @abstractmethod
    def stats_by_class(self, camera_id: int | None = None) -> dict[str, int]:
        ...
