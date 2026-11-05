# RL-агент для клеточного dungeon crawler

Полный проект: игровой симулятор, обучение RL-агента (PPO из Stable-Baselines3
с кастомным CNN на PyTorch), inference-сервис на FastAPI и телеметрия в Kafka.
Визуализация - pygame.

## Архитектура

```
+------------------+        events          +----------------------+
| Game simulator   |----------------------->| Telemetry collector  |
| (dungeon core)   |   Observer + Event     | (Kafka producer)     |
| Gymnasium env    |   Sourcing             +----------+-----------+
+--------+---------+                                   |
         | obs, reward                                 v
         v                                       Kafka topic
+------------------+                            dungeon-telemetry
| RL trainer       |                                   |
| PPO + CNN (SB3)  |                            +------+------+
| MLflow tracking  |                            | consumer /  |
+--------+---------+                            | dashboard   |
         | model.zip                            +-------------+
         v
+------------------+
| Inference service|
| FastAPI /predict |
+------------------+
```

Компоненты:

* **Game simulator** - ядро игры: генерация подземелья, игрок, враги, ловушки,
  монетки; Gymnasium-обёртка `DungeonGymEnv`.
* **RL trainer** - обучение PPO с кастомным CNN-экстрактором признаков,
  логирование в MLflow, отправка событий в Kafka.
* **Inference service** - FastAPI-эндпоинт `/predict`, возвращает действие
  агента по наблюдению; `/health` для проб.
* **Telemetry collector** - подписчик-Observer, публикует каждое событие
  симуляции в Kafka; консьюмер агрегирует поток и печатает сводку.

## Паттерны и где они живут

| Паттерн | Где | Зачем |
|---|---|---|
| State | `src/game/state_machine.py` | Explore/Combat/Flee - поведение скриптованного агента и разметка эпизодов |
| Strategy | `src/game/strategies.py` | Сменное поведение врагов: random / patrol / chase |
| Observer | `src/game/events.py` (EventBus) | Рассылка событий подписчикам (телеметрия, рендер) |
| Command | `src/game/commands.py` | Действия игрока как объекты; удобно логировать и повторять |
| Factory | `src/game/map_gen.py`, `src/game/commands.py`, `src/factories/env_factory.py` | Генерация уровней, команд и обучающих окружений |
| Event Sourcing | `src/game/events.py` (EventStore) | Append-only журнал всех изменений мира, replay истории |

## Быстрый старт (локально)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

make random        # случайный агент - проверить окружение
make test          # pytest
make train         # обучение PPO (по умолчанию 200k шагов)
make play          # посмотреть обученного агента в pygame
make robot         # бейзлайн на конечном автомате
```

## Быстрый старт (Docker)

```bash
make docker-up     # kafka, mlflow, trainer, inference, consumer
# после обучения:
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
     -d "$(python scripts/predict_payload.py)"
```

## Наблюдение и награды

Наблюдение - тензор `[6, H, W]`: стены, игрок (яркость = доля HP), враги,
монетки, активные ловушки, «зоны опасности» вокруг врагов.

Награды (настраиваются в `config/config.yaml`): шаг `-0.01`, монетка `+1`,
ловушка `-1`, удар врага `-1`, победа (все монетки) `+10`, смерть `-5`.

## Структура

```
rl-dungeon-crawler/
├── config/config.yaml          # параметры мира, наград, обучения, kafka, mlflow
├── src/
│   ├── game/                   # ядро симулятора (паттерны + Gym env)
│   ├── rl/                     # trainer: PPO, CNN, колбэки MLflow/телеметрия
│   ├── inference/              # FastAPI-сервис
│   ├── telemetry/              # Kafka producer + consumer
│   ├── factories/              # EnvFactory
│   ├── rendering/              # pygame-рендер
│   └── utils/
├── scripts/                    # random_agent, robot_agent (State FSM), play
├── tests/                      # pytest: шаги, команды, FSM, replay событий
├── Dockerfile
├── docker-compose.yml
└── Makefile
```
