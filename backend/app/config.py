"""
Application Configuration and Environment Settings.
Enforces CRITICAL-RULES §8: IRDAI Licence Number is loaded exclusively via environment config.
"""

import os
import platform
import shutil
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root, i.e. the directory holding backend/ and frontend/.
# The .env path is anchored to it because a bare ".env" resolves against the
# current working directory: running the app from the repo root found the file,
# running alembic from backend/ did not, and the database URL silently fell back
# to the built-in default port.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_libreoffice() -> str:
    """
    Where to find headless LibreOffice for DOCX to PDF conversion.

    This was a fixed /usr/bin path, which cannot exist on the Windows machines
    the tool is developed and demonstrated on, so PDF download failed there with
    a file-not-found error rather than anything that pointed at the cause.
    """
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    if platform.system() == "Windows":
        return r"C:\Program Files\LibreOffice\program\soffice.exe"
    return "/usr/bin/libreoffice"


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
    APP_ACCESS_PASSWORD: str = os.getenv("APP_ACCESS_PASSWORD", "surveyor123")

    # Surveyor Licensing (CRITICAL RULE 8: Must come from environment)
    IRDAI_LICENCE_NUMBER: str = os.getenv("IRDAI_LICENCE_NUMBER", "")

    # File Storage Paths
    STORAGE_DIR: Path = Path("./storage")
    UPLOAD_DIR: Path = Path("./storage/uploads")
    DERIVED_DIR: Path = Path("./storage/derived")
    TEMPLATES_DIR: Path = Path("./templates")

    # Headless LibreOffice
    LIBREOFFICE_BINARY: str = _default_libreoffice()

    # ------------------------------------------------------------------
    # Reading handwritten tally sheets
    # ------------------------------------------------------------------
    # The sheets are pen on a pre-printed form, photographed on a phone, often
    # sideways, often with highlighter over the subtotal rows. A local OCR
    # engine does not cope with that. A hosted vision model does, so it is the
    # primary reader when a key is configured, and the local engine is the
    # fallback for when it is not.
    #
    # Primary means it reads first, not that it is believed. Everything it
    # returns lands in the Verification Workbench flagged for checking, and the
    # row arithmetic is proved against the total written on the sheet before
    # anything can be saved.
    #
    # Confidentiality: the sheet carries the MCA letterhead, the party name and
    # the container number, and free API tiers generally permit the provider to
    # retain what is submitted. TALLY_CLOUD_SEND_FULL_SHEET decides whether the
    # header band goes with it. Sending it means the model also fills in party,
    # container, dates, room and brix; withholding it means the surveyor types
    # those six fields and only the number grid leaves the building.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    # Asked at the same time as GEMINI_MODEL; the first usable answer wins.
    # Comma-separated so a retired or newly released model can be swapped in
    # from .env without touching code.
    GEMINI_FALLBACK_MODELS: str = os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.8-flash,gemini-flash-latest,gemini-3.5-flash",
    )
    TALLY_CLOUD_SEND_FULL_SHEET: bool = os.getenv("TALLY_CLOUD_SEND_FULL_SHEET", "true").lower() in ("true", "1", "yes")
    # Per request, and for the whole attempt across every model and round.
    TALLY_CLOUD_TIMEOUT_SECONDS: int = 60
    TALLY_CLOUD_TOTAL_BUDGET_SECONDS: int = int(os.getenv("TALLY_CLOUD_TOTAL_BUDGET_SECONDS", "75"))

    # CORS Allowed Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
