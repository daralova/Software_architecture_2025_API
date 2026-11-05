"""Рендер симулятора на pygame (опциональная зависимость)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..game.dungeon import DungeonSimulator

CELL = 24
COLOR_BG = (18, 18, 24)
COLOR_WALL = (70, 70, 90)
COLOR_FLOOR = (38, 38, 50)
COLOR_PLAYER = (80, 220, 120)
COLOR_ENEMY = (220, 80, 80)
COLOR_COIN = (240, 200, 60)
COLOR_TRAP = (160, 60, 200)
COLOR_HUD = (230, 230, 230)


class PygameRenderer:
    def __init__(self, sim: "DungeonSimulator", caption: str = "RL Dungeon Crawler") -> None:
        import pygame
        self.pygame = pygame
        pygame.init()
        self.sim = sim
        self.cell = CELL
        size = (sim.width * CELL, sim.height * CELL + 30)
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption(caption)
        self.font = pygame.font.SysFont("monospace", 16)
        self.clock = pygame.time.Clock()
        self.last_frame = None

    def draw(self) -> None:
        pygame = self.pygame
        sim = self.sim
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                raise SystemExit
        self.screen.fill(COLOR_BG)
        for y in range(sim.height):
            for x in range(sim.width):
                rect = pygame.Rect(x * self.cell, y * self.cell, self.cell, self.cell)
                color = COLOR_WALL if sim.grid[y, x] == 0 else COLOR_FLOOR
                pygame.draw.rect(self.screen, color, rect)
        for trap in sim.traps:
            if trap.armed:
                self._dot(trap.x, trap.y, COLOR_TRAP)
        for coin in sim.coins:
            self._dot(coin.x, coin.y, COLOR_COIN)
        for enemy in sim.enemies:
            self._dot(enemy.x, enemy.y, COLOR_ENEMY)
        self._dot(sim.player.x, sim.player.y, COLOR_PLAYER)
        hud = f"HP {sim.player.hp}  SCORE {sim.player.score}  STEP {sim.tick}  EP {sim.episode}"
        text = self.font.render(hud, True, COLOR_HUD)
        self.screen.blit(text, (6, sim.height * self.cell + 4))
        pygame.display.flip()
        self.clock.tick(30)
        self.last_frame = pygame.surfarray.array3d(self.screen).transpose(1, 0, 2)

    def _dot(self, x: int, y: int, color) -> None:
        r = self.cell // 3
        self.pygame.draw.circle(
            self.screen, color,
            (x * self.cell + self.cell // 2, y * self.cell + self.cell // 2),
            r,
        )

    def close(self) -> None:
        self.pygame.quit()
