"""Frame extraction: выбор ключевых кадров (каждый N-й) + предобработка."""
from app.pipeline.base import Stage, FrameContext

class FrameExtractionStage(Stage):
    name = "frame_extraction"

    def __init__(self, target_size: tuple[int, int] = (1024, 576)):
        self.target_size = target_size

    def process(self, ctx: FrameContext) -> FrameContext:
        # точка расширения: ресайз, выравнивание яркости, денойз и т.д.
        return ctx
