from app.observers.base import Observer
from app.core.logging import get_logger

class LoggingObserver(Observer):
    def __init__(self, every_n: int = 50):
        self.every_n = every_n
        self.count = 0
        self.log = get_logger("observer")

    def update(self, event: str, **payload):
        if event == "frame_done":
            self.count += 1
            if self.count % self.every_n == 0:
                self.log.info("Обработано кадров: %s, событий в последнем: %s",
                              self.count, payload.get("events"))
        elif event == "stage_error":
            self.log.error("Ошибка на стадии %s: %s",
                           payload.get("stage"), payload.get("error"))
