"""
Application Configuration and Environment Settings.
Enforces CRITICAL-RULES §8: IRDAI Licence Number is loaded exclusively via environment config.
"""

import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Marine Cargo Survey & QC Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Union[str, bool, int]) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "debug", "dev")
        return False

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5433/marine_survey"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5433/marine_survey"
    )

    # Redis & Sessions
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SESSION_TTL_SECONDS: int = 86400  # 24 hours
    SESSION_COOKIE_SECURE: bool = False
    ALLOW_FAKE_REDIS: bool = os.getenv("ALLOW_FAKE_REDIS", "true").lower() in ("true", "1", "yes")

    # Security & Hashing
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "insecure-dev-secret-change-in-production-32-chars"
    )

    # Surveyor Licensing (CRITICAL RULE 8: Must come from environment)
    IRDAI_LICENCE_NUMBER: str = os.getenv("IRDAI_LICENCE_NUMBER", "")

    # File Storage Paths
    STORAGE_DIR: Path = Path("./storage")
    UPLOAD_DIR: Path = Path("./storage/uploads")
    DERIVED_DIR: Path = Path("./storage/derived")
    TEMPLATES_DIR: Path = Path("./templates")

    # Headless LibreOffice
    LIBREOFFICE_BINARY: str = "/usr/bin/libreoffice"

    # CORS Allowed Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
