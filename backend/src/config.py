"""Centralized application configuration via Pydantic Settings.

All environment variable reads are consolidated here. Import ``settings``
for the validated settings instance.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required (no defaults — must be set in environment or .env):
        - mongodb_uri  (MONGODB_URI)
        - jwt_secret   (JWT_SECRET)

    Optional with sensible defaults:
        - reasoning_model (CANON_REASONING_MODEL)
        - fast_model      (CANON_FAST_MODEL)
        - embedding_model (CANON_EMBEDDING_MODEL)
        - jwt_algorithm   (JWT_ALGORITHM)
        - jwt_expiry_days (JWT_EXPIRY_DAYS)
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ─── Required Secrets ─────────────────────────────────────────────────
    mongodb_uri: str
    jwt_secret: str

    # ─── Model Configuration ─────────────────────────────────────────────
    reasoning_model: str = Field(
        default="gemini-3.1-pro",
        validation_alias=AliasChoices("CANON_REASONING_MODEL", "reasoning_model"),
    )
    fast_model: str = Field(
        default="gemini-3.1-flash",
        validation_alias=AliasChoices("CANON_FAST_MODEL", "fast_model"),
    )
    embedding_model: str = Field(
        default="text-embedding-004",
        validation_alias=AliasChoices("CANON_EMBEDDING_MODEL", "embedding_model"),
    )

    # ─── Database Configuration ────────────────────────────────────────────
    database_name: str = "canon"

    # ─── Environment ─────────────────────────────────────────────────────
    environment: str = "production"

    # ─── JWT Configuration ───────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 7


# Eagerly instantiated — resolves .env on first import.
settings = Settings()  # type: ignore[call-arg]
