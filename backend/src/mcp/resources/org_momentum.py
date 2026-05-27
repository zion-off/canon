from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bson import ObjectId
from mcp.server.fastmcp import Context

from src.mcp.context import build_context
from src.models.documents import MemoryNodeDocument


async def get_org_momentum(ctx: Context | None = None) -> str:
    """Organizational momentum — recent trajectory and evolution.

    Synthesizes recently captured decisions, discoveries, and changes into
    a projection of where the organization is heading.
    """
    if ctx is None:
        raise RuntimeError("Context required — FastMCP should inject it automatically.")
    request_ctx = await build_context(ctx)
    cutoff = datetime.now(UTC) - timedelta(days=30)
    tenant_oid = ObjectId(request_ctx.tenant_id)
    nodes = (
        await MemoryNodeDocument.find(
            MemoryNodeDocument.tenant_id == tenant_oid,
            MemoryNodeDocument.updated_at >= cutoff,
        )
        .sort("-updatedAt")
        .to_list(length=200)
    )

    return _format_as_org_momentum(nodes)


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
