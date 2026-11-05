import numpy as np
import pytest
import cv2
from app.pipeline.base import FrameContext
from app.pipeline.stages.analytics import ObjectAnalyticsStage, AreaSpeedEstimator
from app.observers import MetricsObserver

def _synthetic_mask(h=360, w=640):
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(mask, (50, 200), (150, 280), 1, -1)   # car
    cv2.rectangle(mask, (300, 150), (450, 300), 2, -1)  # bus
    cv2.rectangle(mask, (500, 180), (610, 290), 3, -1)  # truck
    return mask

def test_analytics_finds_three_objects():
    stage = ObjectAnalyticsStage(storage=None, producer=None)
    ctx = FrameContext(camera_id=1, frame_index=0,
                       image=np.zeros((360, 640, 3), dtype=np.uint8),
                       mask=_synthetic_mask())
    out = stage.process(ctx)
    classes = sorted(e["class_name"] for e in out.events)
    assert classes == ["bus", "car", "truck"]
    assert all(e["pixel_area"] > 0 for e in out.events)

def test_speed_strategy_monotonic():
    s = AreaSpeedEstimator()
    assert s.estimate(1000, 640) is not None
    assert s.estimate(1000, 640) < s.estimate(10000, 640)

def test_metrics_observer_counts():
    obs = MetricsObserver()
    obs.update("frame_done", events=3)
    obs.update("frame_done", events=1)
    snap = obs.snapshot()
    assert snap["frames"] == 2 and snap["events"] == 4
