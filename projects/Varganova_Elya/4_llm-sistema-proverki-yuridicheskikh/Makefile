.PHONY: up down logs demo test seed reindex

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f api worker

demo:
	python scripts/demo.py

test:
	pytest tests -v

seed:
	python scripts/seed_legal_knowledge.py
