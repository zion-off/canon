"""Centralized MCP configuration via Pydantic Settings.

All environment variable reads are consolidated here. Import ``settings``
for the validated settings instance.
"""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MCP server settings loaded from environment variables.

    Required:
        - canon_api_token  (CANON_API_TOKEN)

    Optional with sensible defaults:
        - canon_backend_url (CANON_BACKEND_URL)
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ─── Canon Backend ────────────────────────────────────────────────────
    canon_backend_url: str = Field(
        default="http://localhost:8000",
        validation_alias="CANON_BACKEND_URL",
    )

    @model_validator(mode="after")
    def _strip_trailing_slash(self) -> Settings:
        self.canon_backend_url = self.canon_backend_url.rstrip("/")
        return self

    # ─── Authentication ───────────────────────────────────────────────────
    canon_api_token: str = Field(
        default="",
        validation_alias="CANON_API_TOKEN",
    )


settings = Settings()
