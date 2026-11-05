"""Video ingestion: выбор источника кадров (Adapter) под нужный stride."""
from app.pipeline.base import Stage, FrameContext
from app.adapters.camera_adapter import make_source
from app.core.config import settings

class IngestionStage(Stage):
    """Фиксирует метаданные источника; сам поток кадров управляется снаружи."""
    name = "ingestion"

    def __init__(self, source: str, frame_index: int = 0):
        self.source_url = source
        self.frame_index = frame_index

    def process(self, ctx: FrameContext) -> FrameContext:
        ctx.frame_index = self.frame_index
        return ctx
