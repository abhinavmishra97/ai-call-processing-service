from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Call Processing Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    # Defaulting to SQLite for local development without Docker
    # To use Postgres, update the DATABASE_URL or set environment variables
    
    @property
    def DATABASE_URL(self) -> str:
        # Use SQLite by default if no env vars are strictly enforced
        # You can toggle this back to Postgres when ready
        return "sqlite+aiosqlite:///./ai_call_service.db"
        
        # Uncomment for Postgres:
        # return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Postgres settings (kept for reference)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "ai_call_service"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
