from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "edustream-service"
    service_port: int = 8300
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://edustream:edustream@postgres:5432/edustream"
    redis_url: str = "redis://redis:6379/0"
    storage_endpoint: str = "minio:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "edustream"

    jwt_secret: str = "edustream-dev-secret"
    encryption_key: str = "edustream-dev-encryption-key"

    video_load_target_seconds: float = 3.0
    webinar_viewers_target: int = 10000
    recommendation_accuracy_target: float = 80.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
