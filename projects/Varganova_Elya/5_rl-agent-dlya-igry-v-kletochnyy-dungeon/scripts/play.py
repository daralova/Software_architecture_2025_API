"""Просмотр обученного агента в pygame.

    python scripts/play.py --model models/ppo_dungeon.zip
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stable_baselines3 import PPO

from src.game.env import DungeonGymEnv
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--model", default="models/ppo_dungeon.zip")
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()

    try:
        import pygame  # noqa: F401
    except ImportError:
        print("Установите pygame: pip install pygame")
        sys.exit(1)

    cfg = load_config(args.config)
    env = DungeonGymEnv(cfg, render_mode="human")
    model = PPO.load(args.model, device="cpu")

    for ep in range(args.episodes):
        env.reset()
        done, total, info = False, 0.0, {}
        while not done:
            action, _ = model.predict(obs := env.sim.observation(), deterministic=True)
            _, reward, terminated, truncated, info = env.step(int(action))
            total += reward
            env.render()
            done = terminated or truncated
        print(f"episode {ep + 1}: reward={total:.2f} score={info.get('score')} hp={info.get('hp')}")
    env.close()


if __name__ == "__main__":
    main()
