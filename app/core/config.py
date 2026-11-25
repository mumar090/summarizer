from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Every value can be overridden via env vars or `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Summarizer API"
    ENV: str = "local"
    LOG_LEVEL: str = "INFO"

    # Database. The API uses the async driver; the Celery worker uses a sync engine
    # derived from the same URL (see `sync_database_url`).
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/summarizer.db"

    # Celery broker. Task state lives in the database, so no result backend is needed.
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_BASE_SECONDS: int = 10

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:1b"
    LLM_TIMEOUT_SECONDS: int = 120  # CPU inference on long chunks is slow
    LLM_TEMPERATURE: float = 0.2

    # Fetching
    FETCH_TIMEOUT_SECONDS: int = 20
    FETCH_MAX_BYTES: int = 5_000_000
    FETCH_MAX_REDIRECTS: int = 5
    ALLOW_PRIVATE_URLS: bool = False  # SSRF protection; only enable for local testing

    # Summarization limits
    SUMMARY_CHAR_LIMIT: int = 1500
    MAX_CHARS_PER_CHUNK: int = 6000
    CHUNK_OVERLAP_CHARS: int = 300
    MAX_INPUT_CHARS: int = 100_000
    MIN_CONTENT_CHARS: int = 100

    @property
    def sync_database_url(self) -> str:
        # postgresql+psycopg works for both sync and async engines; SQLite needs the driver swapped.
        return self.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")


settings = Settings()
