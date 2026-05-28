"""Prompt endpoints — serve prompt text for MCP proxy consumption.

Auth: Bearer API token (resolved via TenantContext).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.dependencies import api_token_auth
from src.services.tenant_resolver import TenantContext

router = APIRouter(tags=["prompts"])


@router.get("/before-implementing")
async def get_before_implementing(
    _: TenantContext = Depends(api_token_auth),
) -> str:
    return (
        "Invoke the `canon` tool whenever you are about to recommend an implementation "
        "approach, make an architectural choice, select a technology or library, or give "
        "any advice that commits the engineer to a direction. Canon holds organizational "
        "memory that the codebase cannot tell you — and your recommendation may be "
        "technically correct but organizationally wrong without this context.\n\n"
        "When invoking: set `request` to describe the engineering intent (what you intend "
        "to recommend and why). Set `context` to summarize what you have already observed "
        "— the current technology stack, existing patterns, scope of the change, and any "
        "relevant codebase details.\n\n"
        "If Canon returns a reshaped plan, use that plan instead of your original "
        "recommendation."
    )


@router.get("/reflect-session")
async def get_reflect_session(
    _: TenantContext = Depends(api_token_auth),
) -> str:
    return (
        "Invoke the `canon` tool with a `request` summarizing what was accomplished in this "
        "session: decisions made, patterns discovered, constraints encountered, failures and "
        "their resolutions, and anything the team should know going forward. Include what "
        "was attempted, what was rejected and why, and what was left unresolved.\n\n"
        "Use this prompt at the end of a work session to ensure organizational knowledge is "
        "current and nothing important is lost."
    )


@router.get("/remember-decision")
async def get_remember_decision(
    _: TenantContext = Depends(api_token_auth),
) -> str:
    return (
        "Invoke the `canon` tool with a `request` that clearly states the decision, "
        "constraint, or pattern you want to capture — include the reasoning, alternatives "
        "considered and rejected, and any relationships to existing systems or decisions. "
        "Provide enough context (technology stack, affected systems, ownership) so Canon "
        "can link this memory to the right entities.\n\n"
        "Use this prompt after making a significant design choice, discovering a "
        "non-obvious constraint, or establishing a pattern others should follow."
    )
