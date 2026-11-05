"""Factory: генерация чертежа подземелья по конфигу.

DungeonFactory инкапсулирует способ постройки уровня (комнаты +
коридоры + случайная расстановка сущностей). Симулятор не знает, КАК
создаётся карта - он получает готовый чертёж.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

WALL = 0
FLOOR = 1


@dataclass
class DungeonBlueprint:
    grid: np.ndarray
    player_spawn: Tuple[int, int]
    enemy_spawns: List[Tuple[int, int]] = field(default_factory=list)
    coin_spawns: List[Tuple[int, int]] = field(default_factory=list)
    trap_spawns: List[Tuple[int, int]] = field(default_factory=list)


class DungeonFactory:
    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng

    def create(
        self,
        width: int,
        height: int,
        rooms: int,
        room_min_size: int,
        coins: int,
        traps: int,
        enemies: int,
    ) -> DungeonBlueprint:
        grid = np.full((height, width), WALL, dtype=np.int8)
        room_rects: List[Tuple[int, int, int, int]] = []

        for _ in range(rooms):
            rw = int(self.rng.integers(room_min_size, room_min_size + 3))
            rh = int(self.rng.integers(room_min_size, room_min_size + 3))
            rx = int(self.rng.integers(1, max(2, width - rw - 1)))
            ry = int(self.rng.integers(1, max(2, height - rh - 1)))
            self._carve_room(grid, rx, ry, rw, rh)
            room_rects.append((rx, ry, rw, rh))

        for (ax, ay, aw, ah), (bx, by, bw, bh) in zip(room_rects, room_rects[1:]):
            self._carve_corridor(
                grid,
                (ax + aw // 2, ay + ah // 2),
                (bx + bw // 2, by + bh // 2),
            )

        floor_cells = [
            (x, y)
            for y in range(1, height - 1)
            for x in range(1, width - 1)
            if grid[y, x] == FLOOR
        ]
        if len(floor_cells) < coins + traps + enemies + 1:
            raise ValueError("Dungeon too small for requested entities")

        self.rng.shuffle(floor_cells)
        player_spawn = tuple(floor_cells[0])
        enemy_spawns = [tuple(c) for c in floor_cells[1 : 1 + enemies]]
        coin_spawns = [tuple(c) for c in floor_cells[1 + enemies : 1 + enemies + coins]]
        trap_spawns = [
            tuple(c)
            for c in floor_cells[1 + enemies + coins : 1 + enemies + coins + traps]
        ]
        return DungeonBlueprint(grid, player_spawn, enemy_spawns, coin_spawns, trap_spawns)

    def _carve_room(self, grid: np.ndarray, x: int, y: int, w: int, h: int) -> None:
        grid[y : y + h, x : x + w] = FLOOR

    def _carve_corridor(self, grid: np.ndarray, a: Tuple[int, int], b: Tuple[int, int]) -> None:
        ax, ay = a
        bx, by = b
        if self.rng.random() < 0.5:
            self._carve_h(grid, ax, bx, ay)
            self._carve_v(grid, ay, by, bx)
        else:
            self._carve_v(grid, ay, by, ax)
            self._carve_h(grid, ax, bx, by)

    def _carve_h(self, grid: np.ndarray, x1: int, x2: int, y: int) -> None:
        lo, hi = sorted((x1, x2))
        grid[y, lo : hi + 1] = FLOOR

    def _carve_v(self, grid: np.ndarray, y1: int, y2: int, x: int) -> None:
        lo, hi = sorted((y1, y2))
        grid[lo : hi + 1, x] = FLOOR
