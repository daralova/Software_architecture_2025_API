"""Factory: сборка обучающих окружений из конфига."""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecEnv

from src.game.env import DungeonGymEnv


def build_env(cfg: Dict[str, Any], seed: int = 0, monitor: bool = True):
    env = DungeonGymEnv(cfg, seed=seed)
    if monitor:
        env = Monitor(env)
    return env


class EnvFactory:
    """Создаёт векторизованное окружение для обучения."""

    @staticmethod
    def create_train_vecenv(cfg: Dict[str, Any], n_envs: int, seed: int = 0) -> VecEnv:
        def _make(rank: int) -> Callable[[], DungeonGymEnv]:
            return lambda: build_env(cfg, seed=seed + rank)

        env_fns: List[Callable[[], DungeonGymEnv]] = [_make(i) for i in range(n_envs)]
        if n_envs > 1:
            return SubprocVecEnv(env_fns)
        return DummyVecEnv(env_fns)
