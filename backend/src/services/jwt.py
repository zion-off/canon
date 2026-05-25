"""JWT token issuance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt as pyjwt

from src.config import settings


def issue_jwt(
    user_id: str,
    email: str,
    name: str,
    tenant_id: str | None,
    role: str | None,
) -> str:
    """Issue a signed JWT with configurable expiry.

    Uses the algorithm and secret from centralized settings.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "tenantId": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expiry_days),
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
