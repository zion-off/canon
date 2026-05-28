"""Resource endpoints — org-state and org-momentum for MCP proxy consumption.

Auth: Bearer API token (resolved via TenantContext).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from beanie.odm.operators.find.comparison import In
from bson import ObjectId
from fastapi import APIRouter, Depends

from src.constants import Status
from src.dependencies import api_token_auth
from src.models.documents import MemoryNodeDocument
from src.services.tenant_resolver import TenantContext

router = APIRouter(tags=["resources"])

_RESOURCE_NODE_LIMIT = 200


@router.get("/org-state")
async def get_org_state(
    ctx: TenantContext = Depends(api_token_auth),
) -> str:
    """Synthesized organizational posture — what the org is currently doing.

    Projects the organization's active decisions, ongoing work, enforced
    patterns, and live constraints into a coherent situational awareness picture.
    """
    tenant_oid = ObjectId(ctx.tenant_id)
    nodes = await MemoryNodeDocument.find(
        MemoryNodeDocument.tenant_id == tenant_oid,
        In(MemoryNodeDocument.status, [Status.ACTIVE, Status.IN_PROGRESS]),
    ).to_list(length=_RESOURCE_NODE_LIMIT)

    return _format_as_org_state(nodes)


@router.get("/org-momentum")
async def get_org_momentum(
    ctx: TenantContext = Depends(api_token_auth),
) -> str:
    """Organizational momentum — recent trajectory and evolution.

    Synthesizes recently captured decisions, discoveries, and changes into
    a projection of where the organization is heading.
    """
    cutoff = datetime.now(UTC) - timedelta(days=30)
    tenant_oid = ObjectId(ctx.tenant_id)
    nodes = (
        await MemoryNodeDocument.find(
            MemoryNodeDocument.tenant_id == tenant_oid,
            MemoryNodeDocument.updated_at >= cutoff,
        )
        .sort("-updatedAt")
        .to_list(length=_RESOURCE_NODE_LIMIT)
    )

    return _format_as_org_momentum(nodes)


def _format_as_org_state(nodes: list[MemoryNodeDocument]) -> str:
    """Format active/in_progress nodes as organizational state projection."""
    if not nodes:
        return "No active organizational state recorded yet."

    active = [n for n in nodes if n.status == Status.ACTIVE]
    in_progress = [n for n in nodes if n.status == Status.IN_PROGRESS]

    sections: list[str] = []

    if active:
        sections.append("## Active Decisions & Constraints\n")
        for node in active:
            sections.append(f"- **{node.name}**: {node.description or ''}")
            if node.tags:
                sections.append(f"  Tags: {', '.join(node.tags)}")

    if in_progress:
        sections.append("\n## In Progress\n")
        for node in in_progress:
            sections.append(f"- **{node.name}**: {node.description or ''}")
            if node.tags:
                sections.append(f"  Tags: {', '.join(node.tags)}")

    return "\n".join(sections)


def _format_as_org_momentum(nodes: list[MemoryNodeDocument]) -> str:
    """Format recently updated nodes as organizational momentum projection."""
    if not nodes:
        return "No recent organizational activity recorded."

    sections: list[str] = ["## Recent Organizational Activity (last 30 days)\n"]

    for node in nodes[:50]:
        date_str = (
            node.updated_at.strftime("%Y-%m-%d") if node.updated_at else "unknown"
        )
        sections.append(
            f"- [{date_str}] **{node.name}** ({node.status}): {node.description or ''}"
        )

    if len(nodes) > 50:
        sections.append(f"\n_... and {len(nodes) - 50} more entries_")

    return "\n".join(sections)
