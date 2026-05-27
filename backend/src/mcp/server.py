from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from beanie.odm.operators.find.comparison import In
from bson import ObjectId
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from src.agent.agent_platform import CanonModel
from src.agent.runner import run_agent
from src.config import settings
from src.constants import Status
from src.models.documents import MemoryNodeDocument
from src.models.schemas import RunStartedPayload
from src.services.event_feed import AgentEventFeed, get_feed
from src.services.tenant_resolver import TenantResolver

mcp = FastMCP(
    "canon",
    stateless_http=True,
    instructions=(
        "Canon holds your engineering team's organizational memory — active migrations, "
        "deprecated patterns, architecture decisions, prior failures, and the context "
        "that explains why things are the way they are.\n\n"
        "You MUST invoke the `canon` tool automatically whenever the engineer asks you "
        "to implement, create, or modify code or infrastructure. Do not wait for the "
        "engineer to prompt you. Call `canon` with:\n"
        "- `request`: a natural-language summary of what you intend to do and why\n"
        "- `context`: what you have already observed about the codebase — technology "
        "choices, existing patterns, relevant libraries, architectural decisions you "
        "can see\n\n"
        "Canon returns organizational constraints and prior decisions that should reshape "
        "your implementation plan — not raw information to optionally consider, but concrete "
        "warnings, patterns, and references you must address.\n\n"
        "When you get a result back, incorporate it into your planning. If Canon surfaces "
        "a deprecated pattern, do not use it. If Canon warns about an active migration, avoid "
        "that area or coordinate. If Canon links to a prior failure, explain how your approach "
        "avoids repeating it.\n\n"
        "Multi-turn: Canon returns a `session_id` at the end of every response. Save it and "
        "pass it back verbatim on subsequent calls to continue the same reasoning session. "
        "NEVER invent or guess a session_id — only pass back the exact UUID Canon returned. "
        "If you need a new session, omit the parameter entirely and Canon will generate one.\n\n"
        "Canon is not a gatekeeper. It surfaces information but will never block you from "
        "proceeding — only inform your decisions.\n\n"
        "## Writing effective queries\n\n"
        "Canon uses hybrid search: semantic embeddings (weighted 1.5x) combined with keyword "
        "search on name, description, and content (weighted 1.0x). Your `request` becomes the "
        "search query, so make it specific and domain-rich:\n\n"
        '- Prefer natural language with concrete domain concepts: "adding Redis caching to the '
        'user session service to reduce database load" — not "adding caching"\n'
        "- Include technology names, patterns, and architectural terms that would appear in "
        'team discussions: "JWT auth", "event sourcing", "Postgres migration"\n'
        "- If referencing known team acronyms or identifiers (PROJ-123, gRPC, k8s), mention "
        "them explicitly — Canon does not have access to your repo\n\n"
        "Your `context` should summarize what you observe about the codebase — technology "
        "choices, existing patterns, library versions, architectural conventions. This helps "
        "Canon contextualize what it retrieves, but it is not used as a search query.\n\n"
        "## What Canon remembers and how\n\n"
        "When Canon persists organizational knowledge, it structures it as named memory nodes "
        "with these fields that affect future retrieval quality:\n\n"
        "- **name and description**: embedded for semantic search AND indexed for keyword "
        "search. These carry the most retrieval weight — make them precise and descriptive.\n"
        "- **content**: the first 1500 characters are embedded for semantic search (the full "
        "content is stored and keyword-searchable). Front-load key concepts, decisions, and "
        "their rationale early in the content field.\n"
        "- **status** (active, deprecated, in_progress, resolved, completed): embedded "
        "alongside the name and keyword-searchable. Canon weights active and in_progress "
        "nodes highest in its reasoning.\n"
        '- **tags**: embedded for semantic search (appended as "Tags: X, Y" to the embedding '
        "text). Use tags for concepts that matter for retrieval but aren't explicit in the "
        "description — categorizations, domains, technology families.\n"
        "- **relationships**: nodes can link to other nodes (relatedEntityIds) and supersede "
        "old ones (supersedes). Canon traces these relationships during graph exploration to "
        "surface connected context."
    ),
    streamable_http_path="/",
)


# --- Context resolution ---


class _RequestContext:
    """Request-scoped dependency container resolved from MCP context."""

    def __init__(
        self,
        tenant_id: str,
        user_id: str,
        event_feed: AgentEventFeed,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.event_feed = event_feed


async def _build_context(ctx: Context) -> _RequestContext:
    """Extract tenant context from the MCP request's underlying HTTP transport."""
    request = ctx.request_context.request
    if request is None:
        raise ValueError("No HTTP request available in MCP context")
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    log = logging.getLogger(__name__)
    log.debug(
        "build_context: resolving tenant from token prefix=%s...",
        token[:8] if token else "(none)",
    )
    resolver = TenantResolver()
    tenant_ctx = await resolver.resolve(token)

    if not tenant_ctx:
        log.warning("build_context: invalid API token")
        raise ValueError("Invalid API token")

    log.info(
        "build_context: resolved | tenant=%s user=%s",
        tenant_ctx.tenant_id,
        tenant_ctx.user_id,
    )
    return _RequestContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        event_feed=get_feed(),
    )


# --- Tool ---


@mcp.tool(
    name="canon",
    annotations=ToolAnnotations(
        title="check organizational memory",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def canon(
    request: str,
    context: str = "",
    session_id: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Check organizational memory before planning or implementing code changes.

    Call this BEFORE writing or modifying any code. It queries your team's
    organizational knowledge graph for deprecated patterns, active migrations,
    architecture decisions, prior failures, and relevant context — and returns
    actionable guidance that should reshape your implementation plan.

    Args:
        request: Natural-language summary of what you intend to implement and why.
        context: What you have observed about the codebase — technology choices,
            existing patterns, relevant libraries, architectural decisions visible
            in the code.
        session_id: MUST be a UUID Canon returned in a previous response. NEVER
            invent, guess, or generate this value. Omit it on the first call —
            Canon will return one. On subsequent calls within the same session,
            pass back exactly the session_id Canon gave you.
        ctx: FastMCP Context — injected automatically.

    Returns:
        Organizational guidance with a session_id for multi-turn continuity.
        Always capture the session_id from the response and pass it back on
        the next call. Do not modify it.
    """
    if ctx is None:
        raise RuntimeError("Context required — FastMCP should inject it automatically.")
    request_ctx = await _build_context(ctx)
    run_id = str(uuid4())

    if session_id is not None:
        try:
            UUID(session_id)
        except ValueError:
            return (
                "ERROR: The session_id you provided is not a valid UUID. "
                "Canon only accepts session IDs it originally generated. "
                "Omit session_id to start a new session, or pass back exactly "
                "the session_id value from a previous Canon response."
            )

    resolved_session_id = session_id or str(uuid4())

    log = logging.getLogger(__name__)
    log.info(
        "canon tool: invoked | tenant=%s session=%s run=%s new_session=%s request=%.120s",
        request_ctx.tenant_id,
        resolved_session_id,
        run_id,
        session_id is None,
        request,
    )

    title = await _generate_title(request)
    log.debug("canon tool: generated title | run=%s title=%s", run_id, title)

    response = await run_agent(
        tenant_id=request_ctx.tenant_id,
        user_id=request_ctx.user_id,
        session_id=resolved_session_id,
        resolved_from_closed=session_id is not None,
        run_id=run_id,
        title=title,
        message=f"Request:\n{request}\n\nContext:\n{context}",
        event_feed=request_ctx.event_feed,
        invocation_args=RunStartedPayload(request=request, context=context),
    )

    return (
        f"{response}\n\n---\nsession_id: {resolved_session_id}\n"
        f"(Save this session_id and pass it back on your next canon call "
        f"to continue this session.)"
    )


# --- Resources ---


@mcp.resource("canon://org/state")
async def get_org_state(ctx: Context | None = None) -> str:
    """Synthesized organizational posture — what the org is currently doing.

    Projects the organization's active decisions, ongoing work, enforced
    patterns, and live constraints into a coherent situational awareness picture.
    """
    if ctx is None:
        raise RuntimeError("Context required — FastMCP should inject it automatically.")
    request_ctx = await _build_context(ctx)
    tenant_oid = ObjectId(request_ctx.tenant_id)
    nodes = await MemoryNodeDocument.find(
        MemoryNodeDocument.tenant_id == tenant_oid,
        In(MemoryNodeDocument.status, [Status.ACTIVE, Status.IN_PROGRESS]),
    ).to_list(length=200)

    return _format_as_org_state(nodes)


@mcp.resource("canon://org/momentum")
async def get_org_momentum(ctx: Context | None = None) -> str:
    """Organizational momentum — recent trajectory and evolution.

    Synthesizes recently captured decisions, discoveries, and changes into
    a projection of where the organization is heading.
    """
    if ctx is None:
        raise RuntimeError("Context required — FastMCP should inject it automatically.")
    request_ctx = await _build_context(ctx)
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


# --- Prompt ---


@mcp.prompt("before-implementing")
def before_implementing_prompt() -> str:
    """Before I implement something — check org memory for conflicts and constraints."""
    return """\
Before implementing: invoke the `canon` tool with `request` describing what you
intend to build and why, and `context` summarizing what you have already observed
about the codebase — technology choices, existing patterns, relevant libraries.
Canon will return organizational constraints — deprecated patterns, active
migrations, prior failures — that should reshape your plan.

Use this prompt whenever you are about to write or modify code and want to ensure
your approach aligns with current team conventions."""


@mcp.prompt("remember-decision")
def remember_decision_prompt() -> str:
    """Remember a decision, constraint, or pattern the team should know about."""
    return """\
Invoke the `canon` tool with a `request` that clearly states the decision, constraint,
or pattern you want to capture — include the reasoning, alternatives considered and
rejected, and any relationships to existing systems or decisions. Provide enough
context (technology stack, affected systems, ownership) so Canon can link this
memory to the right entities.

Use this prompt after making a significant design choice, discovering a non-obvious
constraint, or establishing a pattern others should follow."""


@mcp.prompt("reflect-session")
def reflect_session_prompt() -> str:
    """Reflect on the current session — capture what was learned, changed, or decided."""
    return """\
Invoke the `canon` tool with a `request` summarizing what was accomplished in this
session: decisions made, patterns discovered, constraints encountered, failures and
their resolutions, and anything the team should know going forward. Pass the exact
`session_id` Canon returned earlier — do not modify or invent it.

Use this prompt at the end of a work session to ensure organizational knowledge is
up to date and nothing important is lost."""


# --- Formatting helpers ---


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


async def _generate_title(request: str) -> str:
    """Generate a 5-6 word title from the raw request. Falls back to truncation."""
    prompt = f"""\
Generate a concise title (5-6 words max) for a coding session based on this request.
Return ONLY the title — no quotes, no preamble, no explanation.

Request: {request[:500]}

Title:"""

    try:
        title = await CanonModel.generate_text(settings.fast_model, prompt)
        if title:
            return title.strip()
    except Exception:
        logging.getLogger(__name__).exception("Title generation failed")

    return request[:100]


def _format_as_org_momentum(nodes: list[MemoryNodeDocument]) -> str:
    """Format recently updated nodes as organizational momentum projection."""
    if not nodes:
        return "No recent organizational activity recorded."

    sections: list[str] = ["## Recent Organizational Activity (last 30 days)\n"]

    for node in nodes[:50]:  # Cap display to 50 most recent
        date_str = (
            node.updated_at.strftime("%Y-%m-%d") if node.updated_at else "unknown"
        )
        sections.append(
            f"- [{date_str}] **{node.name}** ({node.status}): {node.description or ''}"
        )

    if len(nodes) > 50:
        sections.append(f"\n_... and {len(nodes) - 50} more entries_")

    return "\n".join(sections)
