"""Запуск пайплайна: сборка стадий, подписка наблюдателей, поток из источника."""
import argparse
from app.adapters.camera_adapter import make_source
from app.adapters.kafka_adapter import KafkaEventProducer
from app.adapters.minio_adapter import ObjectStorage
from app.pipeline import Pipeline
from app.pipeline.base import FrameContext
from app.pipeline.stages.frame_extractor import FrameExtractionStage
from app.pipeline.stages.segmentation import SegmentationStage
from app.pipeline.stages.analytics import ObjectAnalyticsStage
from app.pipeline.stages.storage import StorageStage
from app.observers import MetricsObserver, LoggingObserver
from app.repositories import SqlDetectionRepository
from app.core.config import settings
from app.core.logging import get_logger
import app.models  # noqa: F401 — регистрация стратегий в фабрике

log = get_logger("run")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="путь к видео или rtsp://...")
    ap.add_argument("--camera-id", type=int, default=1)
    ap.add_argument("--model", default=None, help="unet | segformer")
    ap.add_argument("--stride", type=int, default=settings.frame_stride)
    args = ap.parse_args()

    producer = KafkaEventProducer()
    storage = ObjectStorage()
    pipeline = Pipeline([
        FrameExtractionStage(),
        SegmentationStage(model_name=args.model, storage=storage),
        ObjectAnalyticsStage(storage=storage, producer=producer),
        StorageStage(repo=SqlDetectionRepository()),
    ])
    metrics = MetricsObserver()
    pipeline.subscribe(metrics).subscribe(LoggingObserver(every_n=10))

    source = make_source(args.source, stride=args.stride)
    log.info("Источник: %s, модель: %s", args.source, args.model or settings.model_name)
    try:
        for idx, frame in source.frames():
            ctx = FrameContext(camera_id=args.camera_id, frame_index=idx, image=frame)
            result = pipeline.run(ctx)
            log.info("Кадр %s: %s событий", idx, len(result.events))
    except KeyboardInterrupt:
        pass
    finally:
        source.release()
        producer.close()
        log.info("Итог: %s", metrics.snapshot())

if __name__ == "__main__":
    main()
