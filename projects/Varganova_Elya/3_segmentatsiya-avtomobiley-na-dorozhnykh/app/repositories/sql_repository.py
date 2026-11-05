from sqlalchemy import select, func
from app.db.database import SessionLocal
from app.db.models import DetectionEvent
from app.repositories.base import DetectionRepository, EventRecord

class SqlDetectionRepository(DetectionRepository):
    """PostgreSQL-реализация Repository. Доменный код про SQL не знает ничего."""

    def add_event(self, **kwargs) -> int:
        with SessionLocal() as db:
            row = DetectionEvent(**kwargs)
            db.add(row)
            db.commit()
            return row.id

    def list_events(self, camera_id=None, class_name=None, limit=100):
        stmt = select(DetectionEvent).order_by(DetectionEvent.id.desc()).limit(limit)
        if camera_id is not None:
            stmt = stmt.where(DetectionEvent.camera_id == camera_id)
        if class_name:
            stmt = stmt.where(DetectionEvent.class_name == class_name)
        with SessionLocal() as db:
            rows = db.scalars(stmt).all()
            return [EventRecord(
                camera_id=r.camera_id, frame_key=r.frame_key, mask_key=r.mask_key,
                class_name=r.class_name, pixel_area=r.pixel_area,
                centroid_x=r.centroid_x, centroid_y=r.centroid_y,
                bbox_x1=r.bbox_x1, bbox_y1=r.bbox_y1, bbox_x2=r.bbox_x2, bbox_y2=r.bbox_y2,
                speed_kmh=r.speed_kmh, created_at=r.created_at) for r in rows]

    def stats_by_class(self, camera_id=None):
        stmt = select(DetectionEvent.class_name, func.count()).group_by(DetectionEvent.class_name)
        if camera_id is not None:
            stmt = stmt.where(DetectionEvent.camera_id == camera_id)
        with SessionLocal() as db:
            return dict(db.execute(stmt).all())
