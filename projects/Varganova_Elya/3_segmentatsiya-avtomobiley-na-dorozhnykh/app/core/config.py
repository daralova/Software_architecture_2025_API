from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://traffic:traffic@postgres:5432/traffic"
    kafka_bootstrap: str = "kafka:9092"
    kafka_topic: str = "traffic-events"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "traffic-frames"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    model_name: str = "unet"          # unet | segformer
    device: str = "cuda"              # cuda | cpu
    frame_stride: int = 10
    min_blob_area: int = 150
    classes: tuple = ("car", "bus", "truck")

    class Config:
        env_file = ".env"

settings = Settings()
