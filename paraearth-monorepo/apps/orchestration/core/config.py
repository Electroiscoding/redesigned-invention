import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/paraearth")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()