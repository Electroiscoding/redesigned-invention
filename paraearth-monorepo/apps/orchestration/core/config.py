import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = os.getenv("REDIS_URL") or "redis://localhost:6379"

    _db_url = os.getenv("DATABASE_URL")
    if not _db_url:
        import warnings
        warnings.warn("DATABASE_URL not set in environment. Falling back to local dev database.")
        _db_url = "postgresql://postgres:postgres@localhost:5432/paraearth_local"
    database_url: str = _db_url

    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()