"""Backend environment configuration."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Session configuration
    SESSION_STORAGE_PATH: Path = Path("./sessions")
    SESSION_TIMEOUT_HOURS: int = 24
    MAX_FILE_SIZE_MB: int = 50
    MAX_FILES_PER_SESSION: int = 10

    # Server configuration
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # LLM configuration
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    LLM_MAX_RETRIES: int = 3
    LLM_INITIAL_DELAY: float = 1.0
    LLM_BACKOFF_MULTIPLIER: float = 2.0
    ANALYSIS_MAX_TURNS: int = 10

    # Supabase configuration
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_KEY: str | None = None

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def SESSIONS_PATH(self) -> Path:
        """Return sessions path as Path object."""
        return Path(self.SESSION_STORAGE_PATH)

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """Return max file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
