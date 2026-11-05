"""Паттерн Command: действие игрока — объект с методом execute.

Движение, ожидание и атака — самостоятельные команды. Environment
получает целочисленный action от агента, а CommandFactory превращает
его в готовую команду. Такой подход упрощает запись действий в журнал,
undo/redo и повтор эпизода из событий.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dungeon import DungeonSimulator


class Command(ABC):
    @abstractmethod
    def execute(self, sim: "DungeonSimulator") -> None:
        ...


class WaitCommand(Command):
    def execute(self, sim: "DungeonSimulator") -> None:
        pass  # игрок пропускает ход


class MoveCommand(Command):
    def __init__(self, dx: int, dy: int) -> None:
        self.dx = dx
        self.dy = dy

    def execute(self, sim: "DungeonSimulator") -> None:
        sim.move_player(self.dx, self.dy)


class CommandFactory:
    """Factory: int action -> Command. 0 = ожидание, 1-4 = направление."""

    _moves = [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]  # stay, up, down, left, right

    def create(self, action: int) -> Command:
        if not 0 <= action < len(self._moves):
            raise ValueError(f"Unknown action: {action}")
        dx, dy = self._moves[action]
        if (dx, dy) == (0, 0):
            return WaitCommand()
        return MoveCommand(dx, dy)
