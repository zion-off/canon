"""Prompt definitions — fetched from the Canon backend."""

from __future__ import annotations

import httpx
from fastmcp.prompts import prompt

from src.config import settings
from src.constants import APIRoute, AuthScheme, HttpHeader, PromptName


async def _fetch_prompt(name: str) -> str:
    async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as client:
        resp = await client.get(
            f"{settings.canon_backend_url}{APIRoute.PROMPTS}/{name}",
            headers={HttpHeader.AUTHORIZATION: f"{AuthScheme.BEARER} {settings.canon_api_token}"},
        )
        resp.raise_for_status()
        return resp.text


@prompt(PromptName.BEFORE_IMPLEMENTING)
async def before_implementing_prompt() -> str:
    """Before implementing any non-trivial change — check org memory for conventions, patterns, and constraints that may affect your approach."""
    return await _fetch_prompt(PromptName.BEFORE_IMPLEMENTING)


@prompt(PromptName.REFLECT_SESSION)
async def reflect_session_prompt() -> str:
    """Reflect on the current session — capture what was learned, changed, or decided."""
    return await _fetch_prompt(PromptName.REFLECT_SESSION)


@prompt(PromptName.REMEMBER_DECISION)
async def remember_decision_prompt() -> str:
    """Remember a decision, constraint, or pattern the team should know about."""
    return await _fetch_prompt(PromptName.REMEMBER_DECISION)
