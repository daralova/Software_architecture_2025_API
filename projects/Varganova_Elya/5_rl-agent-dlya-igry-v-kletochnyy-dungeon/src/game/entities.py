from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .strategies import EnemyStrategy


@dataclass
class Entity:
    x: int
    y: int


@dataclass
class Player(Entity):
    hp: int = 10
    max_hp: int = 10
    score: int = 0
    kills: int = 0


@dataclass
class Enemy(Entity):
    hp: int = 2
    damage: int = 1
    strategy: Optional["EnemyStrategy"] = None
    kind: str = "grunt"


@dataclass
class Coin(Entity):
    value: int = 1


@dataclass
class Trap(Entity):
    damage: int = 1
    armed: bool = True
