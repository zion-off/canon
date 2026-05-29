"""Authentication helpers: JWT issuance, API token generation and hashing."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import jwt as pyjwt

from src.config import settings
from src.models.schemas import JwtPayload


class AuthService:
    """Centralised authentication operations for JWT and API token lifecycle."""

    @staticmethod
    def issue_jwt(
        user_id: str,
        email: str,
        name: str,
        tenant_id: str | None,
        role: str | None,
        lifetime: timedelta | None = None,
    ) -> str:
        """Sign and return a JWT for the given user identity.

        Uses ``settings.jwt_expiry_days`` by default; pass a custom
        ``lifetime`` for short-lived variants such as stream tokens.
        """
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "tenantId": tenant_id,
            "role": role,
            "iat": now,
            "exp": now + (lifetime or timedelta(days=settings.jwt_expiry_days)),
        }
        return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    @staticmethod
    def issue_stream_token(user: JwtPayload) -> str:
        """Issue a short-lived JWT for SSE stream access.

        Carries the same claims as the user's session JWT but with a
        reduced expiry suited for query-param delivery to EventSource
        connections, which cannot set Authorization headers.
        """
        return AuthService.issue_jwt(
            user.sub,
            user.email,
            user.name,
            user.tenant_id,
            user.role,
            timedelta(hours=settings.stream_token_expiry_hours),
        )

    @staticmethod
    def generate_api_token() -> str:
        """Generate a random API token with the ``ct_`` prefix.

        Returns the raw token — show it to the user once, then store
        only the result of ``hash_token()`` in the database.
        """
        return f"ct_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_token(raw: str) -> str:
        """Return the hex-encoded SHA-256 hash of a raw API token.

        Tokens are stored hashed so a database breach does not expose
        usable credentials. The raw token is never persisted.
        """
        return sha256(raw.encode()).hexdigest()
