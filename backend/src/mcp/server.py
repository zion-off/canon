from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from bson import ObjectId
from mcp.server.fastmcp import Context, FastMCP

from src.mcp.runner import run_agent
from src.services.tenant_resolver import TenantResolver

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

    from src.services.event_feed import AgentEventFeed


mcp = FastMCP(
    "Canon",
    stateless_http=True,
    instructions="Ambient organizational continuity agent for engineering teams.",
)


# --- Context resolution ---

class _RequestContext:
    """Request-scoped dependency container resolved from MCP context."""

    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        db: AsyncIOMotorDatabase,
        event_feed: AgentEventFeed,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.db = db
        self.event_feed = event_feed


async def _build_context(ctx: Context) -> _RequestContext:
    """Extract tenant context from the MCP request's underlying HTTP transport."""
    request = ctx.request
    db = request.app.state.mongo.db

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    resolver = TenantResolver(db)
    tenant_ctx = await resolver.resolve(token)

    if not tenant_ctx:
        raise ValueError("Invalid API token")

    return _RequestContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        db=db,
        event_feed=request.app.state.event_feed,
    )


# --- Tool ---

@mcp.tool(
    name="canon",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def canon(
    request: str,
    context: str = "",
    session_id: str | None = None,
    ctx: Context = None,
) -> str:
    """Invoke Canon's organizational continuity agent.

    Args:
        request: What to analyze, remember, or ask about. Natural language.
        context: Code context — file paths, function signatures, dependencies.
        session_id: Optional session ID to continue a prior workflow session.
            Omit on first call — Canon will generate one and return it.
        ctx: FastMCP Context — injected automatically by the framework.

    Returns:
        Agent response with session_id for workflow continuity.
    """
    request_ctx = await _build_context(ctx)
    run_id = str(uuid4())
    resolved_session_id = session_id or str(uuid4())

    response = await run_agent(
        tenant_id=request_ctx.tenant_id,
        user_id=request_ctx.user_id,
        session_id=resolved_session_id,
        run_id=run_id,
        message=f"Request:\n{request}\n\nContext:\n{context}",
        event_feed=request_ctx.event_feed,
        db=request_ctx.db,
    )

    return f"{response}\n\n---\nsession_id: {resolved_session_id}"


# --- Resources ---

@mcp.resource("canon://org/state")
async def get_org_state(ctx: Context = None) -> str:
    """Synthesized organizational posture — what the org is currently doing.

    Projects the organization's active decisions, ongoing work, enforced
    patterns, and live constraints into a coherent situational awareness picture.
    """
    request_ctx = await _build_context(ctx)
    nodes = await request_ctx.db.memory_nodes.find(
        {
            "tenantId": ObjectId(request_ctx.tenant_id),
            "status": {"$in": ["active", "in_progress"]},
        },
        {"_id": 0, "embedding": 0, "embeddingText": 0},
    ).to_list(length=200)

    return _format_as_org_state(nodes)


@mcp.resource("canon://org/momentum")
async def get_org_momentum(ctx: Context = None) -> str:
    """Organizational momentum — recent trajectory and evolution.

    Synthesizes recently captured decisions, discoveries, and changes into
    a projection of where the organization is heading.
    """
    request_ctx = await _build_context(ctx)
    cutoff = datetime.now(UTC) - timedelta(days=30)
    nodes = await request_ctx.db.memory_nodes.find(
        {
            "tenantId": ObjectId(request_ctx.tenant_id),
            "updatedAt": {"$gte": cutoff},
        },
        {"_id": 0, "embedding": 0, "embeddingText": 0},
    ).sort("updatedAt", -1).to_list(length=200)

    return _format_as_org_momentum(nodes)


# --- Prompt ---

@mcp.prompt("canon-behavior")
def canon_behavior_prompt() -> str:
    """Core behavioral instructions for Canon-enabled coding sessions."""
    return """You have access to Canon, your team's organizational continuity companion.
Canon holds the accumulated knowledge of your engineering organization — decisions
made, constraints discovered, patterns established, and context that would otherwise
be lost between conversations.

## Before Implementing

Before writing or modifying code, call `canon` with:
- `request`: What you are about to do and why
- `context`: The relevant code context (file paths, function signatures, dependencies)

Canon will surface relevant organizational context — prior decisions that apply,
constraints you should know about, patterns being followed, or ongoing work that
might conflict. Incorporate what Canon returns into your approach.

Canon always returns a `session_id` at the end of its response. Pass it in
subsequent calls to maintain continuity within the same logical task. On first
call, omit `session_id` — Canon generates one. On subsequent calls, pass the
`session_id` Canon gave you.

## Remembering Through Conversation

At natural checkpoints in your work — when a decision is made, a constraint is
discovered, or a pattern emerges — share it with Canon as part of the natural
flow of conversation:

- "We decided to use event sourcing for billing because X, Y, Z"
- "Discovered the payment gateway has a 30-second timeout"
- "Going forward, new services expose health checks on /healthz"

Call `canon` with what was learned and the surrounding context. Canon determines
what to persist and how to connect it to existing organizational knowledge.
There is no special ceremony — the conversation itself is the interface for
organizational memory.

Good moments to share with Canon:
- A design decision and the reasoning behind it
- A non-obvious constraint discovered during implementation
- A pattern that should be followed going forward
- A dependency or relationship not obvious from code alone
- An alternative that was considered and rejected (and why)

Don't over-report. Not every line of code is organizational knowledge. Canon is
for the things that would be painful to rediscover — the context that makes
future decisions faster and better.

## How Canon Works

Canon is a reasoning companion, not a gatekeeper. It provides context that helps
engineers make informed decisions. When you share something with Canon, it reasons
about where that knowledge fits in the organization's memory, how it connects to
what's already known, and whether it changes existing understanding. Canon will
tell you what it did — you'll see the reasoning naturally in the conversation.

Your goal together is organizational continuity: ensuring that knowledge earned
through engineering effort persists and informs future work."""


# --- Formatting helpers ---

def _format_as_org_state(nodes: list[dict]) -> str:
    """Format active/in_progress nodes as organizational state projection."""
    if not nodes:
        return "No active organizational state recorded yet."

    active = [n for n in nodes if n.get("status") == "active"]
    in_progress = [n for n in nodes if n.get("status") == "in_progress"]

    sections: list[str] = []

    if active:
        sections.append("## Active Decisions & Constraints\n")
        for node in active:
            sections.append(f"- **{node.get('name', 'Unnamed')}**: {node.get('description', '')}")
            if node.get("tags"):
                sections.append(f"  Tags: {', '.join(node['tags'])}")

    if in_progress:
        sections.append("\n## In Progress\n")
        for node in in_progress:
            sections.append(f"- **{node.get('name', 'Unnamed')}**: {node.get('description', '')}")
            if node.get("tags"):
                sections.append(f"  Tags: {', '.join(node['tags'])}")

    return "\n".join(sections)


def _format_as_org_momentum(nodes: list[dict]) -> str:
    """Format recently updated nodes as organizational momentum projection."""
    if not nodes:
        return "No recent organizational activity recorded."

    sections: list[str] = ["## Recent Organizational Activity (last 30 days)\n"]

    for node in nodes[:50]:  # Cap display to 50 most recent
        updated = node.get("updatedAt")
        date_str = updated.strftime("%Y-%m-%d") if updated else "unknown"
        status = node.get("status", "unknown")
        sections.append(
            f"- [{date_str}] **{node.get('name', 'Unnamed')}** ({status}): "
            f"{node.get('description', '')}"
        )

    if len(nodes) > 50:
        sections.append(f"\n_... and {len(nodes) - 50} more entries_")

    return "\n".join(sections)
