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
        "Consult Canon before you commit the engineer to a technical direction. "
        "Canon holds your team's accumulated knowledge about how they build software — "
        "conventions, patterns, error handling approaches, retry strategies, testing "
        "practices, naming, library choices, architectural decisions, and the reasoning "
        "behind existing code. Any non-trivial coding decision may have organizational "
        "context you should know about. Your recommendation may be technically correct "
        "yet organizationally wrong without it.\n\n"
        "Set `request` to what you intend to do and why — specific and domain-rich, "
        "naming the technologies, services, and patterns involved (Canon cannot see your "
        "repo). Set `context` to what you have already observed: the stack, existing "
        "patterns, scope of the change, and relevant codebase details.\n\n"
        "If Canon reshapes your plan, adopt the reshaped plan instead of your original "
        "recommendation, and make the change visible to the engineer — what you were "
        "about to do, what Canon flagged, and how you are adjusting."
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
