"""Ядро игрового симулятора.

DungeonSimulator сводит воедино все паттерны:
  * Command   - ход игрока выполняется через объекты-команды;
  * Strategy  - враги ходят по сменным стратегиям;
  * Observer  - каждый факт публикуется подписчикам;
  * Event Sourcing - каждый факт попадает в append-only журнал;
  * State     - в info отдаётся текущее состояние агента;
  * Factory   - карта создаётся DungeonFactory, команды CommandFactory.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .commands import CommandFactory
from .entities import Coin, Enemy, Player, Trap
from .events import EventBus, EventStore, EventType, GameEvent
from .map_gen import DungeonFactory, FLOOR, WALL
from .strategies import StrategyFactory
from .state_machine import AgentContext, AgentStateMachine

MOVES = [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]
OBS_CHANNELS = 6  # walls, player, enemies, coins, traps, danger


class DungeonSimulator:
    MOVES = MOVES
    ACTION_NAMES = ["stay", "up", "down", "left", "right"]

    def __init__(self, cfg: Dict[str, Any], seed: Optional[int] = None) -> None:
        self.cfg = cfg
        env_cfg = cfg["env"]
        self.rewards = cfg.get("rewards", {})
        self.width = int(env_cfg["width"])
        self.height = int(env_cfg["height"])
        self.max_steps = int(env_cfg["max_steps"])
        self.rng = np.random.default_rng(seed)
        self.command_factory = CommandFactory()
        self.event_store = EventStore()
        self.bus = EventBus()
        self.state_machine = AgentStateMachine()
        self.tick = 0
        self.episode = 0
        self.step_events: List[GameEvent] = []
        self.reset()

    # ------------------------------------------------------------- reset --
    def reset(self) -> None:
        env_cfg = self.cfg["env"]
        blueprint = DungeonFactory(self.rng).create(
            width=self.width,
            height=self.height,
            rooms=int(env_cfg["rooms"]),
            room_min_size=int(env_cfg.get("room_min_size", 3)),
            coins=int(env_cfg["coins"]),
            traps=int(env_cfg["traps"]),
            enemies=int(env_cfg["enemies"]),
        )
        self.grid = blueprint.grid
        px, py = blueprint.player_spawn
        self.player = Player(x=px, y=py)
        self.coins = [Coin(x=x, y=y) for x, y in blueprint.coin_spawns]
        self.traps = [Trap(x=x, y=y) for x, y in blueprint.trap_spawns]
        strategy_name = env_cfg.get("enemy_strategy", "chase")
        self.enemies = [
            Enemy(x=x, y=y, strategy=StrategyFactory.create(strategy_name))
            for x, y in blueprint.enemy_spawns
        ]
        self.tick = 0
        self.episode += 1
        self.step_events = []
        self._emit(EventType.EPISODE_START, {})

    # ------------------------------------------------------------ helpers --
    def emit(self, etype: EventType, data: Dict[str, Any]) -> None:
        self._emit(etype, data)

    def _emit(self, etype: EventType, data: Dict[str, Any]) -> None:
        event = GameEvent(type=etype, tick=self.tick, episode=self.episode, data=data)
        self.event_store.append(event)
        self.bus.publish(event)
        self.step_events.append(event)

    def is_floor(self, x: int, y: int) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.grid[y, x] == FLOOR

    def enemy_at(self, x: int, y: int) -> Optional[Enemy]:
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y:
                return enemy
        return None

    def can_enemy_step(self, enemy: Enemy, x: int, y: int) -> bool:
        if not self.is_floor(x, y):
            return False
        if self.player.x == x and self.player.y == y:
            return False
        for other in self.enemies:
            if other is not enemy and other.x == x and other.y == y:
                return False
        return True

    # --------------------------------------------------------------- step --
    def step(self, action: int) -> Tuple[float, bool, Dict[str, Any]]:
        self.step_events = []
        self.tick += 1
        reward = float(self.rewards.get("step", -0.01))

        command = self.command_factory.create(action)
        command.execute(self)
        reward += self._check_traps()
        reward += self._move_enemies()
        reward += self._process_coins()

        terminated = False
        truncated = False
        if self.player.hp <= 0:
            terminated = True
            reward += float(self.rewards.get("death", -5.0))
        elif not self.coins:
            terminated = True
            reward += float(self.rewards.get("win", 10.0))
        elif self.tick >= self.max_steps:
            truncated = True

        if terminated or truncated:
            self._emit(
                EventType.EPISODE_END,
                {
                    "reason": "death" if self.player.hp <= 0 else ("win" if not self.coins else "timeout"),
                    "score": self.player.score,
                    "steps": self.tick,
                },
            )
        return reward, terminated or truncated, self._info(truncated)

    def move_player(self, dx: int, dy: int) -> None:
        nx, ny = self.player.x + dx, self.player.y + dy
        if not self.is_floor(nx, ny):
            self._emit(EventType.PLAYER_BLOCKED, {"x": nx, "y": ny})
            return
        self.player.x, self.player.y = nx, ny
        self._emit(EventType.PLAYER_MOVED, {"x": nx, "y": ny})
        enemy = self.enemy_at(nx, ny)
        if enemy is not None:
            self._attack(enemy)

    def _attack(self, enemy: Enemy) -> None:
        enemy.hp -= 1
        self.player.hp -= enemy.damage
        self._emit(EventType.PLAYER_HIT, {"enemy_x": enemy.x, "enemy_y": enemy.y, "player_hp": self.player.hp})
        if enemy.hp <= 0:
            self.enemies.remove(enemy)
            self.player.kills += 1
            self._emit(EventType.ENEMY_KILLED, {"enemy_x": enemy.x, "enemy_y": enemy.y})

    def _process_coins(self) -> float:
        reward = 0.0
        for coin in list(self.coins):
            if coin.x == self.player.x and coin.y == self.player.y:
                self.coins.remove(coin)
                self.player.score += coin.value
                reward += float(self.rewards.get("coin", 1.0))
                self._emit(EventType.COIN_COLLECTED, {"x": coin.x, "y": coin.y, "score": self.player.score})
        return reward

    def _check_traps(self) -> float:
        reward = 0.0
        for trap in self.traps:
            if trap.armed and trap.x == self.player.x and trap.y == self.player.y:
                trap.armed = False
                self.player.hp -= trap.damage
                reward += float(self.rewards.get("trap", -1.0))
                self._emit(EventType.TRAP_TRIGGERED, {"x": trap.x, "y": trap.y, "player_hp": self.player.hp})
        return reward

    def _move_enemies(self) -> float:
        reward = 0.0
        for enemy in list(self.enemies):
            if enemy.hp <= 0:
                continue
            dx, dy = enemy.strategy.next_step(enemy, self)
            nx, ny = enemy.x + dx, enemy.y + dy
            if self.can_enemy_step(enemy, nx, ny):
                enemy.x, enemy.y = nx, ny
            if enemy.x == self.player.x and enemy.y == self.player.y:
                self.player.hp -= enemy.damage
                reward += float(self.rewards.get("hit", -1.0))
                self._emit(EventType.PLAYER_HIT, {"enemy_x": enemy.x, "enemy_y": enemy.y, "player_hp": self.player.hp})
                if enemy.hp <= 0:
                    self.enemies.remove(enemy)
        return reward

    # -------------------------------------------------------- observation --
    def observation(self) -> np.ndarray:
        h, w = self.height, self.width
        obs = np.zeros((OBS_CHANNELS, h, w), dtype=np.float32)
        obs[0][self.grid == WALL] = 1.0
        obs[1][self.player.y, self.player.x] = float(self.player.hp) / self.player.max_hp
        for enemy in self.enemies:
            obs[2][enemy.y, enemy.x] = 1.0
            for dx, dy in MOVES:
                nx, ny = enemy.x + dx, enemy.y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    obs[5][ny, nx] = 1.0
        for coin in self.coins:
            obs[3][coin.y, coin.x] = 1.0
        for trap in self.traps:
            if trap.armed:
                obs[4][trap.y, trap.x] = 1.0
        return obs

    def _info(self, truncated: bool) -> Dict[str, Any]:
        nearest = self._nearest_enemy()
        ctx = AgentContext(
            sim=self,
            hp_ratio=self.player.hp / self.player.max_hp,
            nearest_enemy=nearest,
        )
        state = self.state_machine.update(ctx)
        return {
            "score": self.player.score,
            "hp": self.player.hp,
            "tick": self.tick,
            "episode": self.episode,
            "agent_state": state.name,
            "truncated": truncated,
            "events": self.step_events,
        }

    def _nearest_enemy(self) -> Optional[Tuple[int, Tuple[int, int]]]:
        best = None
        for enemy in self.enemies:
            dx, dy = enemy.x - self.player.x, enemy.y - self.player.y
            dist = abs(dx) + abs(dy)
            if best is None or dist < best[0]:
                best = (dist, (dx, dy))
        return best
