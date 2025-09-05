from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl


class Settings(BaseSettings):
    APP_NAME: str = "Summarizer API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/summarizer.db"

    # Redis
    BROKER_URL: str = "redis://redis:6379/0"
    RESULT_BACKEND: str = "redis://redis:6379/1"

    # Ollama
    OLLAMA_BASE_URL: AnyHttpUrl = "http://ollama:11434"
    OLLAMA_MODEL: str = "gemma3:1b"

    # Limits
    SUMMARY_CHAR_LIMIT: int = 1500
    MAX_CHARS_PER_CHUNK: int = 6000
    REQUEST_TIMEOUT_SECONDS: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
