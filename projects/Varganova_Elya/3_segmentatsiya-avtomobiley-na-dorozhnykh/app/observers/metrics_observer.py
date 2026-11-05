import time
from app.observers.base import Observer

class MetricsObserver(Observer):
    """Считает кадры, события и FPS. В проде легко заменить на Prometheus."""

    def __init__(self):
        self.frames = 0
        self.events = 0
        self.errors = 0
        self._t0 = time.monotonic()

    def update(self, event: str, **payload):
        if event == "frame_done":
            self.frames += 1
            self.events += payload.get("events", 0)
        elif event == "stage_error":
            self.errors += 1

    def snapshot(self) -> dict:
        elapsed = max(time.monotonic() - self._t0, 1e-6)
        return {"frames": self.frames, "events": self.events,
                "errors": self.errors, "fps": round(self.frames / elapsed, 2)}
