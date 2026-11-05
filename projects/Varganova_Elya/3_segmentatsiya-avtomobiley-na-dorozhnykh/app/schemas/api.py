from datetime import datetime
from pydantic import BaseModel

class EventOut(BaseModel):
    id: int
    camera_id: int
    class_name: str
    pixel_area: int
    centroid_x: float
    centroid_y: float
    speed_kmh: float | None
    created_at: datetime

    class Config:
        from_attributes = True

class StatsOut(BaseModel):
    class_name: str
    count: int

class CameraIn(BaseModel):
    name: str
    source_url: str
    location: str = ""
