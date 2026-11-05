"""Pipeline: цепочка стадий + рассылка событий наблюдателям (Observer)."""
from typing import Iterable
from app.pipeline.base import Stage
from app.observers.base import Subject
from app.core.logging import get_logger

log = get_logger("pipeline")

class Pipeline(Subject):
    def __init__(self, stages: Iterable[Stage]):
        self.stages = list(stages)

    def run(self, ctx):
        for stage in self.stages:
            try:
                ctx = stage.process(ctx)
            except Exception as e:
                log.error("Стадия %s упала: %s", stage.name, e)
                self.notify("stage_error", stage=stage.name, error=str(e))
                raise
        self.notify("frame_done", frame_index=ctx.frame_index, events=len(ctx.events))
        return ctx
