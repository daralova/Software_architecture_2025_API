"""Прогон случайного агента: проверка окружения и печати метрик."""
import argparse

from src.factories.env_factory import build_env
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--episodes", type=int, default=10)
    args = parser.parse_args()

    cfg = load_config(args.config)
    env = build_env(cfg, monitor=False)
    for ep in range(args.episodes):
        env.reset()
        done, total = False, 0.0
        info = {}
        while not done:
            action = env.action_space.sample()
            _, reward, terminated, truncated, info = env.step(action)
            total += reward
            done = terminated or truncated
        print(
            f"episode {ep + 1}: reward={total:.2f} score={info.get('score')} "
            f"hp={info.get('hp')} steps={info.get('tick')} state={info.get('agent_state')}"
        )
    env.close()


if __name__ == "__main__":
    main()
