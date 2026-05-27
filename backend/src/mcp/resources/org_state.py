from __future__ import annotations

from beanie.odm.operators.find.comparison import In
from bson import ObjectId
from mcp.server.fastmcp import Context

from src.constants import Status
from src.mcp.context import build_context
from src.models.documents import MemoryNodeDocument


async def get_org_state(ctx: Context | None = None) -> str:
    """Synthesized organizational posture — what the org is currently doing.

    Projects the organization's active decisions, ongoing work, enforced
    patterns, and live constraints into a coherent situational awareness picture.
    """
    if ctx is None:
        raise RuntimeError("Context required — FastMCP should inject it automatically.")
    request_ctx = await build_context(ctx)
    tenant_oid = ObjectId(request_ctx.tenant_id)
    nodes = await MemoryNodeDocument.find(
        MemoryNodeDocument.tenant_id == tenant_oid,
        In(MemoryNodeDocument.status, [Status.ACTIVE, Status.IN_PROGRESS]),
    ).to_list(length=200)

    return _format_as_org_state(nodes)


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
