# LLM-система проверки юридических договоров

Сервис, который принимает договор, разбивает его на пункты, находит рискованные
условия, обогащает находки цитатами из базы юридических знаний (RAG) и
формирует отчёт с резюме.

## Архитектура

```
                        ┌─────────────┐
   POST /contracts ───> │ API Gateway │──> MinIO (файл)
                        │  (FastAPI)  │──> PostgreSQL (запись)
                        └──────┬──────┘──> Kafka (событие contract.uploaded)
                               │
                        ┌──────▼──────┐
                        │   Worker    │──> CommandInvoker -> Command
                        └──────┬──────┘
                               │
                    Document Processing Pipeline:
                    Parse -> Split -> Embed -> RiskScan
                            -> RagEnrichment -> Summarize -> Persist
                               │
                RAG: HybridRetriever (pgvector + Elasticsearch, RRF)
```

## Паттерны проектирования

| Паттерн | Где |
|---|---|
| Facade | `app/facade/facade.py` — единая точка входа для API и воркера |
| Strategy | `app/strategies/` — сплиттеры пунктов и 6 риск-детекторов |
| Adapter | `app/adapters/` — LLM, эмбеддинги, pgvector, ES, MinIO, парсеры |
| Repository | `app/repositories/` — контрактные интерфейсы + in-memory/SQLAlchemy |
| Pipeline | `app/pipeline/` — 7 стадий обработки документа |
| Command | `app/commands/` — команды + invoker, диспатчер событий Kafka |

## Запуск

Полный стек (нужен Docker):

```bash
cp .env.example .env
docker compose up --build -d
```

Демо без инфраструктуры (все бэкенды in-memory):

```bash
python scripts/demo.py
```

Тесты:

```bash
pip install pytest && pytest tests -v
```

## API

- `POST /api/v1/contracts` — загрузить файл (multipart) или `text`; ответ 202 c `contract_id`.
- `GET /api/v1/contracts/{id}` — статус обработки.
- `GET /api/v1/analysis/{id}` — отчёт: пункты, находки с уровнями, цитаты, резюме.
- `GET /api/v1/admin/reindex` — переиндексация базы знаний.
- `GET /api/v1/health` — health-check.

## Включение ML-бэкендов

По умолчанию используются офлайн-заглушки (`hashing`-эмбеддер, `rule-based` LLM).
Для боевого качества:

1. Раскомментируйте зависимости в `requirements.txt`.
2. В `.env`: `EMBEDDING_BACKEND=hf`, `LLM_BACKEND=hf`.
3. Для детекции рисков поверх стратегий можно добавить LLM-анализ как ещё одну
   стратегию в `app/strategies/` — Pipeline и остальные компоненты менять не нужно.
