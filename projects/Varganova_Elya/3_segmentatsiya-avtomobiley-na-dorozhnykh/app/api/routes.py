from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.database import get_db
from app.db.models import Camera
from app.repositories import SqlDetectionRepository
from app.adapters.minio_adapter import ObjectStorage
from app.schemas.api import EventOut, StatsOut, CameraIn

router = APIRouter(prefix="/api/v1", tags=["traffic"])
repo = SqlDetectionRepository()

@router.get("/events", response_model=list[EventOut])
def list_events(camera_id: int | None = None, class_name: str | None = None,
                limit: int = Query(100, le=1000)):
    return repo.list_events(camera_id=camera_id, class_name=class_name, limit=limit)

@router.get("/stats", response_model=list[StatsOut])
def stats(camera_id: int | None = None):
    return [StatsOut(class_name=k, count=v)
            for k, v in repo.stats_by_class(camera_id).items()]

@router.get("/frames/{key}/url")
def frame_url(key: str):
    storage = ObjectStorage()
    url = storage.presigned_url(key)
    if not url:
        raise HTTPException(404, "Кадр не найден")
    return {"url": url}

@router.post("/cameras")
def create_camera(data: CameraIn, db=Depends(get_db)):
    cam = Camera(name=data.name, source_url=data.source_url, location=data.location)
    db.add(cam)
    db.commit()
    return {"id": cam.id, "name": cam.name}
