import os

class Config:
    KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:29092")
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    PG_DSN = os.getenv("PG_DSN", "postgresql://antifraud:antifraudpass@postgres:5432/antifraud")
    XGBOOST_MODEL_PATH = os.getenv("XGBOOST_MODEL_PATH", "models/model.json")
