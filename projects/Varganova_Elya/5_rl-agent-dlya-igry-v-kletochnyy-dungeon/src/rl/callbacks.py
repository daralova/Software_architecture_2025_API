"""Колбэки обучения: MLflow-метрики и телеметрия в Kafka."""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from stable_baselines3.common.callbacks import BaseCallback

if TYPE_CHECKING:
    from ..telemetry.collector import TelemetryCollector


class MLflowEpisodeCallback(BaseCallback):
    """Каждые log_freq завершённых эпизодов пишет средний reward в MLflow."""

    def __init__(self, log_freq: int = 20) -> None:
        super().__init__()
        self.log_freq = log_freq
        self._episode_rewards: List[float] = []
        self._num_episodes = 0

    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        for info in infos:
            if "episode" in info:
                self._episode_rewards.append(info["episode"]["r"])
        if len(self._episode_rewards) >= self.log_freq:
            mean_r = sum(self._episode_rewards) / len(self._episode_rewards)
            try:
                import mlflow
                mlflow.log_metric("mean_episode_reward", mean_r, step=self._num_episodes)
            except Exception:
                pass  # MLflow недоступен - обучение продолжается
            self._episode_rewards.clear()
        return True

    def _on_ep_start(self) -> None:
        self._num_episodes += 1


class TelemetryCallback(BaseCallback):
    """Перенаправляет события симуляции из info в TelemetryCollector (Kafka)."""

    def __init__(self, collector: "TelemetryCollector", flush_every: int = 200) -> None:
        super().__init__()
        self.collector = collector
        self.flush_every = flush_every

    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        for info in infos:
            for event in info.get("events", []):
                self.collector.send(event)
        if self.num_timesteps % self.flush_every == 0:
            self.collector.flush()
        return True
