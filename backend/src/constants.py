"""Domain-wide constants shared across all layers.

Every raw string that represents a domain concept lives here.
No inline strings. No magic values.
"""

from __future__ import annotations

from typing import Final


class Status:
    """Session and memory node status values."""

    ACTIVE: Final = "active"
    IN_PROGRESS: Final = "in_progress"


class Role:
    """Team role values stored in user documents."""

    OWNER: Final = "owner"
    MEMBER: Final = "member"


class SessionState:
    """Keys for FastMCP session state shared between middlewares."""

    TENANT: Final = "_canon_tenant"
    USER: Final = "_canon_user"
