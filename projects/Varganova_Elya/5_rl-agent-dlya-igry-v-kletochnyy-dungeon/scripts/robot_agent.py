"""Скриптованный агент на конечном автомате (State pattern).

Полезен как бейзлайн: с чем сравнивать RL-агента.
"""
import argparse

from src.factories.env_factory import build_env
from src.game.state_machine import AgentContext, AgentStateMachine
from src.utils.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    cfg = load_config(args.config)
    env = build_env(cfg, monitor=False)
    fsm = AgentStateMachine()

    for ep in range(args.episodes):
        env.reset(seed=args.seed + ep)
        done, total = False, 0.0
        info = {}
        while not done:
            sim = env.sim
            nearest = sim._nearest_enemy()
            ctx = AgentContext(
                sim=sim,
                hp_ratio=sim.player.hp / sim.player.max_hp,
                nearest_enemy=nearest,
            )
            state = fsm.update(ctx)
            _, reward, terminated, truncated, info = env.step(state.choose_action(ctx))
            total += reward
            done = terminated or truncated
        print(f"episode {ep + 1}: reward={total:.2f} score={info.get('score')} hp={info.get('hp')} steps={info.get('tick')}")
    env.close()


if __name__ == "__main__":
    main()
