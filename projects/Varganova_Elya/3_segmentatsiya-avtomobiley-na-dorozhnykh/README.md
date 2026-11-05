# Traffic Segmentation — сегментация автомобилей на дорожных камерах

Видеопоток с дорожных камер разбивается на кадры, нейросеть (U-Net или SegFormer)
выделяет пиксельные маски классов car / bus / truck, из масок извлекаются
объекты (контуры, центроиды, площади, скорость), результаты сохраняются
в PostgreSQL + MinIO и доступны через FastAPI.

## Архитектура

```
Video ingestion -> Frame extraction -> Segmentation inference
      -> Object analytics -> Storage (MinIO/PostgreSQL) -> API (FastAPI)
```

## Паттерны

| Паттерн | Где | Зачем |
|---|---|---|
| Pipeline | `app/pipeline/` | последовательная обработка кадров через стадии |
| Adapter | `app/adapters/`, `app/models/segformer.py` | унификация камер, Kafka, MinIO и внешних моделей |
| Strategy | `app/models/factory.py`, `app/analytics` | выбор сегментатора и стратегии оценки скорости на лету |
| Repository | `app/repositories/` | изоляция доступа к БД от доменной логики |
| Observer | `app/observers/` | события пайплайна: метрики, логирование, алерты |

## Быстрый старт

```bash
docker compose up -d                 # kafka, minio, postgres, api
pip install -r requirements.txt
python scripts/init_db.py
python scripts/run_pipeline.py --source rtsp://camera.local/stream --model unet
```

API: http://localhost:8000/docs

## Обучение

`scripts/train_unet.py` — обучение U-Net на масках (например, Cityscapes с
мэппингом классов car / bus / truck). Метрики логируются на каждой эпохе,
лучшая по mIoU модель сохраняется в checkpoints.
