"""Паттерн State: поведение агента зависит от его внутреннего состояния.

ExploreState -> CombatState -> FleeState. Каждый класс состояния решает,
какое действие выдать в текущем контексте, и сам решает, когда уступить
место другому состоянию. Используется скриптованным агентом и для
разметки телеметрии (какое поведение было у агента на каждом шаге).
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from .dungeon import DungeonSimulator


@dataclass
class AgentContext:
    sim: "DungeonSimulator"
    hp_ratio: float
    nearest_enemy: Optional[Tuple[int, Tuple[int, int]]]  # (расстояние, (dx, dy))


class AgentState(ABC):
    name = "state"

    @abstractmethod
    def choose_action(self, ctx: AgentContext) -> int:
        ...

    def on_enter(self, ctx: AgentContext) -> None:
        pass

    def on_exit(self, ctx: AgentContext) -> None:
        pass


class ExploreState(AgentState):
    name = "explore"

    def choose_action(self, ctx: AgentContext) -> int:
        # Грубая эвристика: тянуться к ближайшей монетке.
        sim = ctx.sim
        best, best_dist = 0, math.inf
        for coin in sim.coins:
            d = abs(coin.x - sim.player.x) + abs(coin.y - sim.player.y)
            if d < best_dist:
                best_dist = d
                dx, dy = coin.x - sim.player.x, coin.y - sim.player.y
                if abs(dx) >= abs(dy):
                    best = 4 if dx > 0 else 2
                else:
                    best = 3 if dy > 0 else 1
        return best


class CombatState(AgentState):
    name = "combat"

    def choose_action(self, ctx: AgentContext) -> int:
        if ctx.nearest_enemy is None:
            return 0
        _, (dx, dy) = ctx.nearest_enemy
        if abs(dx) + abs(dy) <= 1:
            return 0  # враг вплотную - осторожно пропускаем ход
        if abs(dx) > abs(dy):
            return 4 if dx > 0 else 2
        return 3 if dy > 0 else 1


class FleeState(AgentState):
    name = "flee"

    def choose_action(self, ctx: AgentContext) -> int:
        if ctx.nearest_enemy is None:
            return 0
        _, (dx, dy) = ctx.nearest_enemy
        if abs(dx) >= abs(dy):
            return 2 if dx > 0 else 4
        return 1 if dy > 0 else 3


class AgentStateMachine:
    """Контекст конечного автомата. Правила переходов зашиты в _choose_state."""

    def __init__(self) -> None:
        self._states = {
            "explore": ExploreState(),
            "combat": CombatState(),
            "flee": FleeState(),
        }
        self._current: AgentState = self._states["explore"]

    @property
    def current(self) -> AgentState:
        return self._current

    def update(self, ctx: AgentContext) -> AgentState:
        target = self._choose_state(ctx)
        if target is not self._current:
            self._current.on_exit(ctx)
            target.on_enter(ctx)
            self._current = target
        return self._current

    def _choose_state(self, ctx: AgentContext) -> AgentState:
        dist = ctx.nearest_enemy[0] if ctx.nearest_enemy else math.inf
        if ctx.hp_ratio <= 0.35 and dist <= 3:
            return self._states["flee"]
        if dist <= 2:
            return self._states["combat"]
        return self._states["explore"]
