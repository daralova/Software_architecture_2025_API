"""Observer: подписчики на события пайплайна."""
from abc import ABC, abstractmethod

class Observer(ABC):
    @abstractmethod
    def update(self, event: str, **payload):
        ...

class Subject:
    def __init__(self):
        self._observers: list[Observer] = []

    def subscribe(self, obs: Observer):
        self._observers.append(obs)
        return self

    def unsubscribe(self, obs: Observer):
        if obs in self._observers:
            self._observers.remove(obs)

    def notify(self, event: str, **payload):
        for obs in list(self._observers):
            try:
                obs.update(event, **payload)
            except Exception:
                pass   # наблюдатель не должен ломать пайплайн
