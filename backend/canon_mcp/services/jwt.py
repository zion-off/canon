"""JWT token issuance."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import jwt as pyjwt


def issue_jwt(
    user_id: str,
    email: str,
    name: str,
    tenant_id: str | None,
    role: str | None,
) -> str:
    """Issue a signed JWT with 7-day expiry.

    Uses HS256 algorithm with JWT_SECRET from environment.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "tenantId": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=7),
    }
    return pyjwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")
