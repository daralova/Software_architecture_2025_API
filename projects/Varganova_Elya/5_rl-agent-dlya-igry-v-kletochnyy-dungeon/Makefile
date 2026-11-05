.PHONY: train test play random robot inference consumer docker-up docker-down

train:
	python -m src.rl.train --config config/config.yaml

test:
	pytest -q tests

play:
	python scripts/play.py

random:
	python scripts/random_agent.py

robot:
	python scripts/robot_agent.py

inference:
	python -m src.inference.service

consumer:
	python -m src.telemetry.consumer

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down -v
