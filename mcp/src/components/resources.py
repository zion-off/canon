"""Resource definitions — fetched from the Canon backend."""

from __future__ import annotations

import httpx
from fastmcp.resources import resource

from src.config import settings
from src.constants import APIRoute, AuthScheme, HttpHeader, ResourcePath, ResourceURI


async def _fetch_resource(path: str) -> str:
    async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as client:
        resp = await client.get(
            f"{settings.canon_backend_url}{APIRoute.RESOURCES}/{path}",
            headers={HttpHeader.AUTHORIZATION: f"{AuthScheme.BEARER} {settings.canon_api_token}"},
        )
        resp.raise_for_status()
        return resp.text


@resource(
    ResourceURI.ORG_MOMENTUM,
    description=(
        "Organizational momentum — recent trajectory and evolution. Review before "
        "making coding decisions to understand what the team is actively working "
        "on and where things are heading."
    ),
)
async def get_org_momentum() -> str:
    """Organizational momentum — recent trajectory and evolution."""
    return await _fetch_resource(ResourcePath.ORG_MOMENTUM)


@resource(
    ResourceURI.ORG_STATE,
    description=(
        "Synthesized organizational posture — what the org is currently doing. "
        "Review before making coding decisions to understand current priorities, "
        "active migrations, and what the team is focused on."
    ),
)
async def get_org_state() -> str:
    """Synthesized organizational posture — what the org is currently doing."""
    return await _fetch_resource(ResourcePath.ORG_STATE)
