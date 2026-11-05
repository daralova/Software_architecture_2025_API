"""Gymnasium-обёртка над симулятором."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .dungeon import OBS_CHANNELS, DungeonSimulator


class DungeonGymEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, cfg: Dict[str, Any], seed: Optional[int] = None, render_mode: Optional[str] = None) -> None:
        super().__init__()
        self.cfg = cfg
        self.render_mode = render_mode
        self.sim = DungeonSimulator(cfg, seed=seed)
        h, w = self.sim.height, self.sim.width
        self.action_space = spaces.Discrete(5)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(OBS_CHANNELS, h, w), dtype=np.float32)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None):
        super().reset(seed=seed)
        self.sim.reset()
        return self.sim.observation(), {"episode": self.sim.episode}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        reward, done, info = self.sim.step(int(action))
        truncated = bool(info.get("truncated", False))
        terminated = done and not truncated
        return self.sim.observation(), reward, terminated, truncated, info

    def render(self):
        if self.render_mode == "human":
            from ..rendering.pygame_renderer import PygameRenderer
            if not hasattr(self, "_renderer"):
                self._renderer = PygameRenderer(self.sim)
            self._renderer.draw()
            return self._renderer.last_frame
        return self.sim.observation()

    def close(self) -> None:
        if hasattr(self, "_renderer"):
            self._renderer.close()
