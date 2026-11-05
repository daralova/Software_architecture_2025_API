"""Паттерн Strategy: поведение врагов вынесено в сменные стратегии.

Одна и та же сущность Enemy может двигаться случайно (RandomStrategy),
патрулировать (PatrolStrategy) или преследовать игрока (ChaseStrategy).
Новая тактика добавляется одним классом и одной записью в реестре.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from .dungeon import DungeonSimulator
    from .entities import Enemy

Step = Tuple[int, int]


class EnemyStrategy(ABC):
    @abstractmethod
    def next_step(self, enemy: "Enemy", sim: "DungeonSimulator") -> Step:
        ...


class RandomStrategy(EnemyStrategy):
    def next_step(self, enemy: "Enemy", sim: "DungeonSimulator") -> Step:
        return random.choice(sim.MOVES)


class PatrolStrategy(EnemyStrategy):
    """Ходит вдоль одной оси, разворачивается у стены."""

    def __init__(self) -> None:
        self.axis = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])

    def next_step(self, enemy: "Enemy", sim: "DungeonSimulator") -> Step:
        dx, dy = self.axis
        if not sim.can_enemy_step(enemy, enemy.x + dx, enemy.y + dy):
            self.axis = (-dx, -dy)
            dx, dy = self.axis
        return (dx, dy)


class ChaseStrategy(EnemyStrategy):
    """Жадный шаг к игроку с обходом стен и других врагов."""

    def next_step(self, enemy: "Enemy", sim: "DungeonSimulator") -> Step:
        player = sim.player
        if player is None:
            return (0, 0)
        candidates: List[Tuple[int, int, int]] = []
        for dx, dy in sim.MOVES:
            nx, ny = enemy.x + dx, enemy.y + dy
            if not sim.can_enemy_step(enemy, nx, ny):
                continue
            dist = abs(nx - player.x) + abs(ny - player.y)
            candidates.append((dist, dx, dy))
        if not candidates:
            return (0, 0)
        candidates.sort()
        _, dx, dy = candidates[0]
        return (dx, dy)


class StrategyFactory:
    """Простая фабрика стратегий по имени из конфига."""

    _registry = {
        "random": RandomStrategy,
        "patrol": PatrolStrategy,
        "chase": ChaseStrategy,
    }

    @classmethod
    def create(cls, name: str) -> EnemyStrategy:
        try:
            return cls._registry[name]()
        except KeyError:
            raise ValueError(f"Unknown enemy strategy: {name!r}")
