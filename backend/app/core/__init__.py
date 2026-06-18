from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — loaded from env / .env file."""

    model_config = SettingsConfigDict(
        env_file=os.fspath(Path(__file__).parents[3] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    APP_NAME: str = "CPIS V1"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Database ---
    DATABASE_URL: PostgresDsn | str = "postgresql+asyncpg://cpis:cpis@localhost:5432/cpis"
    DATABASE_ECHO: bool = False

    # --- Redis ---
    REDIS_URL: RedisDsn | str = "redis://localhost:6379/0"

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- AI (LLM) ---
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_BASE_URL: str = ""

    # --- Feishu ---
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_BITABLE_TOKEN: str = ""

    # --- Collection ---
    COLLECTION_TIMEOUT_SECONDS: int = 60
    COLLECTION_MAX_RETRIES: int = 3
    COLLECTION_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # --- Review ---
    REVIEW_CONFIDENCE_THRESHOLD: float = 0.7

    # --- Auth ---
    SECRET_KEY: str = ""  # Must be set in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
