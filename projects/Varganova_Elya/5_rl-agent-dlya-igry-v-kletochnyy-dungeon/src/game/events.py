"""Event Sourcing + Observer.

Каждое изменение мира фиксируется как неизменяемое событие в append-only
журнале (EventStore). Журнал можно проиграть заново (replay), чтобы
восстановить историю эпизода или передать её в телеметрию. Рассылка
событий подписчикам идёт через EventBus (паттерн Observer).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    EPISODE_START = "episode_start"
    PLAYER_MOVED = "player_moved"
    PLAYER_BLOCKED = "player_blocked"
    COIN_COLLECTED = "coin_collected"
    TRAP_TRIGGERED = "trap_triggered"
    PLAYER_HIT = "player_hit"
    ENEMY_KILLED = "enemy_killed"
    EPISODE_END = "episode_end"


@dataclass(frozen=True)
class GameEvent:
    type: EventType
    tick: int
    episode: int
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "tick": self.tick,
            "episode": self.episode,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class EventStore:
    """Append-only журнал событий (Event Sourcing)."""

    def __init__(self) -> None:
        self._events: List[GameEvent] = []

    def append(self, event: GameEvent) -> None:
        self._events.append(event)

    def all(self) -> List[GameEvent]:
        return list(self._events)

    def replay(self, sink: Callable[[GameEvent], None], episode: Optional[int] = None) -> None:
        """Проигрывает журнал в приёмник (телеметрия, рендер, восстановление)."""
        for event in self._events:
            if episode is None or event.episode == episode:
                sink(event)

    def clear(self) -> None:
        self._events.clear()


class EventBus:
    """Observer: подписчики получают каждое событие симуляции."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[GameEvent], None]] = []

    def subscribe(self, callback: Callable[[GameEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: GameEvent) -> None:
        for callback in self._subscribers:
            callback(event)
