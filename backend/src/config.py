"""Centralized application configuration via Pydantic Settings.

All environment variable reads are consolidated here. Import ``settings``
for the validated, cached singleton instance.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required (no defaults — must be set in environment or .env):
        - mongodb_uri  (MONGODB_URI)
        - jwt_secret   (JWT_SECRET)
        - gemini_api_key (GEMINI_API_KEY)

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
    gemini_api_key: str

    # ─── Model Configuration ─────────────────────────────────────────────
    reasoning_model: str = Field(
        default="gemini-2.5-pro",
        validation_alias=AliasChoices("CANON_REASONING_MODEL", "reasoning_model"),
    )
    fast_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("CANON_FAST_MODEL", "fast_model"),
    )
    embedding_model: str = Field(
        default="text-embedding-004",
        validation_alias=AliasChoices("CANON_EMBEDDING_MODEL", "embedding_model"),
    )

    # ─── JWT Configuration ───────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_expiry_days: int = 7


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


class _SettingsProxy:
    """Lazy proxy that defers Settings instantiation until first attribute access."""

    def __getattr__(self, name: str) -> object:
        return getattr(get_settings(), name)


# Module-level convenience alias for simple attribute access.
settings: Settings = _SettingsProxy()  # type: ignore[assignment]
