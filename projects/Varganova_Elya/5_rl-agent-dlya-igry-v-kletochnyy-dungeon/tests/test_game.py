import numpy as np
import pytest

from src.game.commands import CommandFactory, MoveCommand
from src.game.dungeon import DungeonSimulator
from src.game.env import DungeonGymEnv
from src.game.events import EventType
from src.game.state_machine import AgentContext, AgentStateMachine


@pytest.fixture
def cfg():
    return {
        "env": {
            "width": 16, "height": 16, "rooms": 6, "room_min_size": 3,
            "coins": 4, "traps": 2, "enemies": 2, "enemy_strategy": "chase",
            "max_steps": 100,
        },
        "rewards": {"step": -0.01, "coin": 1.0, "trap": -1.0, "hit": -1.0,
                    "kill": 0.5, "death": -5.0, "win": 10.0},
    }


def test_env_shapes(cfg):
    env = DungeonGymEnv(cfg, seed=0)
    obs, info = env.reset(seed=0)
    assert obs.shape == (6, 16, 16)
    assert obs.dtype == np.float32
    assert env.action_space.contains(4)


def test_sim_step_and_events(cfg):
    sim = DungeonSimulator(cfg, seed=1)
    reward, done, info = sim.step(1)
    assert isinstance(reward, float)
    assert info["tick"] == 1
    # журнал событий содержит минимум episode_start + шаг
    assert len(sim.event_store.all()) >= 2


def test_command_factory(cfg):
    factory = CommandFactory()
    cmd = factory.create(3)
    assert isinstance(cmd, MoveCommand)
    assert cmd.dx == -1 and cmd.dy == 0
    with pytest.raises(ValueError):
        factory.create(99)


def test_state_machine_switch():
    class FakeSim:
        player = None
        coins = []
        enemies = []
    ctx = AgentContext(sim=FakeSim(), hp_ratio=0.2, nearest_enemy=(2, (1, 0)))
    fsm = AgentStateMachine()
    state = fsm.update(ctx)
    assert state.name == "flee"


def test_event_replay(cfg):
    sim = DungeonSimulator(cfg, seed=2)
    for _ in range(5):
        sim.step(int(np.random.randint(0, 5)))
    seen = []
    sim.event_store.replay(lambda e: seen.append(e.type.value))
    assert len(seen) >= 6  # episode_start + шаги
    assert seen[0] == "episode_start"
