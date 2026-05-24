"""Centralized application configuration via Pydantic Settings.

All environment variable reads are consolidated here. Consumers import
``get_settings()`` to access the validated, cached singleton.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required fields (no defaults — must be set in environment or .env):
        - mongodb_uri (MONGODB_URI)
        - jwt_secret (JWT_SECRET)
        - gemini_api_key (GEMINI_API_KEY)

    Optional fields with sensible defaults:
        - reasoning_model (CANON_REASONING_MODEL)
        - fast_model (CANON_FAST_MODEL)
        - embedding_model (CANON_EMBEDDING_MODEL)
        - jwt_algorithm (JWT_ALGORITHM)
        - jwt_expiry_days (JWT_EXPIRY_DAYS)
    """

    model_config = {"env_file": ".env", "extra": "ignore"}

    # ─── Required Secrets ─────────────────────────────────────────────────
    mongodb_uri: str
    jwt_secret: str
    gemini_api_key: str

    # ─── Model Configuration ─────────────────────────────────────────────
    reasoning_model: str = Field(
        default="gemini-2.5-pro",
        validation_alias="CANON_REASONING_MODEL",
    )
    fast_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="CANON_FAST_MODEL",
    )
    embedding_model: str = Field(
        default="text-embedding-004",
        validation_alias="CANON_EMBEDDING_MODEL",
    )

    # ─── JWT Configuration ───────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
