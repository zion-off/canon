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


@resource(ResourceURI.ORG_MOMENTUM)
async def get_org_momentum() -> str:
    """Organizational momentum — recent trajectory and evolution."""
    return await _fetch_resource(ResourcePath.ORG_MOMENTUM)


@resource(ResourceURI.ORG_STATE)
async def get_org_state() -> str:
    """Synthesized organizational posture — what the org is currently doing."""
    return await _fetch_resource(ResourcePath.ORG_STATE)
