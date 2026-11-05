"""Storage stage: пишет события через Repository (изоляция БД)."""
from app.pipeline.base import Stage, FrameContext
from app.repositories.base import DetectionRepository
from app.core.logging import get_logger

log = get_logger("storage")

class StorageStage(Stage):
    name = "storage"

    def __init__(self, repo: DetectionRepository):
        self.repo = repo

    def process(self, ctx: FrameContext) -> FrameContext:
        for ev in ctx.events:
            try:
                self.repo.add_event(
                    camera_id=ev["camera_id"],
                    frame_key=ev["frame_key"] or "",
                    mask_key=ev["mask_key"] or "",
                    class_name=ev["class_name"],
                    pixel_area=ev["pixel_area"],
                    centroid_x=ev["centroid"][0],
                    centroid_y=ev["centroid"][1],
                    bbox_x1=ev["bbox"][0], bbox_y1=ev["bbox"][1],
                    bbox_x2=ev["bbox"][2], bbox_y2=ev["bbox"][3],
                    speed_kmh=ev.get("speed_kmh"),
                )
            except Exception as e:
                log.error("Не удалось записать событие: %s", e)
        return ctx
