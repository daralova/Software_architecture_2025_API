"""Точка входа RL-тренера: PPO + MLflow + телеметрия.

Пример запуска:
    python -m src.rl.train --config config/config.yaml --timesteps 200000
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.factories.env_factory import EnvFactory
from src.rl.callbacks import MLflowEpisodeCallback, TelemetryCallback
from src.rl.networks import DungeonCnn
from src.telemetry.collector import TelemetryCollector
from src.utils.config import load_config


def train(config_path: str, timesteps: int | None = None, seed: int | None = None) -> str:
    cfg = load_config(config_path)
    train_cfg = cfg["training"]
    mlflow_cfg = cfg["mlflow"]

    timesteps = timesteps or int(train_cfg["total_timesteps"])
    seed = seed if seed is not None else int(train_cfg.get("seed", 42))

    mlflow = None
    try:
        import mlflow
        mlflow.set_tracking_uri(mlflow_cfg.get("tracking_uri", "http://localhost:5000"))
        mlflow.set_experiment(mlflow_cfg.get("experiment", "dungeon-crawler"))
        mlflow.start_run(run_name=mlflow_cfg.get("run_name", "ppo"))
        mlflow.log_params({**train_cfg, "seed": seed})
    except Exception:
        print("[train] MLflow недоступен, метрики будут только в консоли")

    vec_env = EnvFactory.create_train_vecenv(cfg, n_envs=int(train_cfg.get("n_envs", 8)), seed=seed)

    from stable_baselines3 import PPO

    policy_kwargs = {
        "features_extractor_class": DungeonCnn,
        "features_extractor_kwargs": {"features_dim": int(train_cfg.get("features_dim", 128))},
    }
    model = PPO(
        "CnnPolicy",
        vec_env,
        learning_rate=float(train_cfg.get("learning_rate", 3e-4)),
        batch_size=int(train_cfg.get("batch_size", 256)),
        gamma=float(train_cfg.get("gamma", 0.99)),
        seed=seed,
        policy_kwargs=policy_kwargs,
        verbose=1,
    )

    collector = TelemetryCollector(cfg)
    callbacks = [MLflowEpisodeCallback(log_freq=20)]
    if collector.enabled:
        callbacks.append(TelemetryCallback(collector))

    model.learn(total_timesteps=timesteps, callback=callbacks, progress_bar=False)

    save_path = str(train_cfg.get("save_path", "models/ppo_dungeon"))
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    model.save(save_path)
    print(f"[train] модель сохранена: {save_path}")

    if mlflow is not None:
        try:
            mlflow.log_artifact(save_path + ".zip", artifact_path="model")
            mlflow.end_run()
        except Exception:
            pass
    vec_env.close()
    collector.close()
    return save_path


def main() -> None:
    parser = argparse.ArgumentParser(description="RL trainer для dungeon crawler")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--timesteps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    train(args.config, args.timesteps, args.seed)


if __name__ == "__main__":
    main()
