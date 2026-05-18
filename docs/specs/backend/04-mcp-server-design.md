# 04 — MCP Server Design

> Ambient interface between organizational memory and coding workflows. Exposes
> organizational awareness as context projections, shapes harness behavior via
> prompts, and provides a single tool endpoint that invokes the ADK agent for
> organizational reasoning and memory persistence.

---

## 1. Server Framework

Canon's MCP server (`canon_mcp`) uses **FastMCP** for MCP transport and
**FastAPI** for REST API routes serving the frontend.

```python
import contextlib
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
from starlette.routing import Mount

mcp = FastMCP(
    "Canon",
    stateless_http=True,
    instructions="Ambient organizational continuity agent for engineering teams.",
)

@contextlib.asynccontextmanager
async def lifespan(app):
    mongo = MongoProvider()
    await mongo.connect()
    app.state.mongo = mongo
    app.state.event_feed = AgentEventFeed(
        event_repo=AgentEventRepository(mongo.db)
    )
    await initialize_agents()  # Spawn MCP subprocesses, attach tools to subagents
    async with mcp.session_manager.run():
        yield
    await mongo.disconnect()

### Module Layout

Route handlers are organized into routers using FastAPI's `APIRouter`.

```
canon_mcp/
├── main.py                  # App composition, lifespan
├── dependencies.py          # FastAPI dependencies (auth, db)
├── routers/
│   ├── auth.py              # register, login, me
│   ├── teams.py             # create, join, invite, tokens
│   ├── sessions.py          # list, create, get, events, stream
│   └── graph.py             # get_graph
├── services/
│   ├── tenant_resolver.py   # TenantResolver
│   └── jwt.py               # issue_jwt helper
└── mcp/
    ├── server.py            # FastMCP instance, tool/resource/prompt defs
    └── agents.py            # initialize_agents, ADK orchestrator
```

### Dependencies

FastAPI dependency injection replaces middleware for auth. Each auth strategy
is a dependency that can be composed into routers:

```python
# dependencies.py
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt

bearer_scheme = HTTPBearer()


async def get_db(request: Request):
    """Database dependency — available to all routes."""
    return request.app.state.mongo.db


async def get_event_feed(request: Request):
    """Event feed dependency."""
    return request.app.state.event_feed


async def jwt_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """JWT auth dependency for frontend routes."""
    try:
        return pyjwt.decode(
            credentials.credentials,
            os.environ["JWT_SECRET"],
            algorithms=["HS256"],
        )
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT")


async def api_token_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TenantContext:
    """API token auth dependency for harness routes."""
    db = request.app.state.mongo.db
    resolver = TenantResolver(db)
    ctx = await resolver.resolve(credentials.credentials)
    if not ctx:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return ctx
```

### Routers

Each router file uses `APIRouter` with the appropriate auth dependency:

```python
# routers/sessions.py
from fastapi import APIRouter, Depends
from dependencies import jwt_auth, api_token_auth, get_db, get_event_feed

# Frontend router — tenant from JWT
router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    tenant_id = user["tenantId"]
    return await db.sessions.find(
        {"tenantId": ObjectId(tenant_id)},
    ).sort("lastRunAt", -1).to_list(length=20)


@router.get("/{session_id}")
async def get_session(session_id: str, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    tenant_id = user["tenantId"]
    return await db.sessions.find_one(
        {"sessionId": session_id, "tenantId": ObjectId(tenant_id)},
    )


@router.get("/{session_id}/events")
async def get_session_events(session_id: str, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    tenant_id = user["tenantId"]
    return await db.agent_events.find(
        {"sessionId": session_id, "tenantId": ObjectId(tenant_id)},
    ).sort("sequence", 1).to_list(length=1000)


@router.get("/{session_id}/stream")
async def session_event_stream(
    session_id: str,
    after: int = 0,
    user: dict = Depends(jwt_auth),
    event_feed=Depends(get_event_feed),
):
    """SSE endpoint — proxied by Next.js route handler. See §6."""
    tenant_id = user["tenantId"]
    ...


# Harness router — tenant from path, API token auth
harness_router = APIRouter(prefix="/tenants/{tenant_id}", tags=["harness-sessions"])


@harness_router.get("/sessions")
async def harness_list_sessions(tenant_id: str, ctx: TenantContext = Depends(api_token_auth), db=Depends(get_db)):
    ...

@harness_router.post("/sessions")
async def harness_create_session(tenant_id: str, ctx: TenantContext = Depends(api_token_auth), db=Depends(get_db)):
    ...

# ... remaining harness CRUD + stream routes follow the same pattern
```

```python
# routers/auth.py
from fastapi import APIRouter, Depends
from dependencies import jwt_auth, get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, db=Depends(get_db)):
    """No auth required."""
    ...


@router.post("/login")
async def login(body: LoginRequest, db=Depends(get_db)):
    """No auth required."""
    ...


@router.get("/me")
async def me(user: dict = Depends(jwt_auth)):
    """Requires JWT auth."""
    return user
```

```python
# routers/teams.py
from fastapi import APIRouter, Depends
from dependencies import jwt_auth, get_db

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("/create")
async def create_team(body: CreateTeamRequest, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    ...

@router.post("/join")
async def join_team(body: JoinTeamRequest, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    ...

@router.post("/invite")
async def create_invite(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    ...

@router.get("/tokens")
async def list_tokens(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    ...

@router.post("/tokens")
async def create_token(body: CreateTokenRequest, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    ...
```

```python
# routers/graph.py
from fastapi import APIRouter, Depends
from dependencies import jwt_auth, get_db

router = APIRouter(tags=["graph"])


@router.get("/graph")
async def get_graph(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """Full memory graph for visualization. Tenant from JWT."""
    tenant_id = user["tenantId"]
    ...
```

### App Composition

FastAPI is the main application. FastMCP is mounted as a Starlette sub-app.
Routers are included under `/api/v1`.

```python
# main.py
from fastapi import FastAPI
from starlette.routing import Mount
from routers import auth, sessions, teams, graph

app = FastAPI(lifespan=lifespan)

# MCP transport — mounted as Starlette sub-app
app.routes.append(Mount("/mcp", app=mcp.streamable_http_app()))

# REST API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(sessions.harness_router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

Auth is enforced per-route via `Depends()` — not via blanket middleware. Public
routes (`/register`, `/login`, `/health`) simply omit the auth dependency.
Protected routes declare their auth dependency explicitly.

### Deployment

- **Runtime**: Cloud Run — stateless, `max_instances=1` (hackathon constraint —
  single instance simplifies SSE fan-out)
- **Transport**: Streamable HTTP via `/mcp/mcp`
- **Python**: 3.14
- **Scaling**: Each tool call is a discrete HTTP request. No in-memory state
  survives between requests.
- **Harness connection**: Cursor, Claude Code, Gemini CLI connect to
  `https://canon-<project>.run.app/mcp/mcp`

### Request Lifecycle

Every MCP operation (tool call, resource fetch, prompt fetch) completes within a
single HTTP request. There is no persistent server-side session state — each
request authenticates, resolves tenant, executes, and returns.

---

## 2. Resources

Resources are **ambient organizational context projections** — synthesized views
of organizational state that give the harness situational awareness. They are
not database queries or CRUD abstractions; they represent Canon's understanding
of what the organization is doing, what it has decided, and what it knows right
now.

### `canon://org/state`

The organization's current operating posture — what's in force, what's in
motion, what the team is actively navigating. This is the organizational present
tense: active decisions being upheld, ongoing work being coordinated, patterns
being enforced.

```python
from mcp.server.fastmcp import Context

@mcp.resource("canon://org/state")
async def get_org_state(ctx: Context = None) -> str:
    """Synthesized organizational posture — what the org is currently doing.

    Projects the organization's active decisions, ongoing work, enforced
    patterns, and live constraints into a coherent situational awareness
    picture. Not a filtered list — a synthesized understanding of the
    organizational present.
    """
    request_ctx = await build_context(ctx)
    nodes = await request_ctx.db.memory_nodes.find(
        {"tenantId": ObjectId(request_ctx.tenant_id), "status": {"$in": ["active", "in_progress"]}},
        {"_id": 0, "embedding": 0},
    ).to_list(length=200)
    return format_as_org_state(nodes)
```

**What this represents**: If a new engineer joined the team today and asked
"what's going on?", this is the answer. Active architectural decisions,
in-flight initiatives, enforced conventions, live constraints. It's
organizational situational awareness compressed into a context window.

### `canon://org/momentum`

The organization's recent trajectory — what's been learned, decided, and
changed. This is organizational movement: the direction the team is heading, the
velocity of knowledge accumulation, and the recency of activity.

```python
@mcp.resource("canon://org/momentum")
async def get_org_momentum(ctx: Context = None) -> str:
    """Organizational momentum — recent trajectory and evolution.

    Synthesizes recently captured decisions, discoveries, and changes into
    a projection of where the organization is heading. Represents the living
    edge of organizational memory — what's fresh, what's evolving, what just
    happened that might affect current work.
    """
    request_ctx = await build_context(ctx)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    nodes = await request_ctx.db.memory_nodes.find(
        {"tenantId": ObjectId(request_ctx.tenant_id), "updatedAt": {"$gte": cutoff}},
        {"_id": 0, "embedding": 0},
    ).sort("updatedAt", -1).to_list(length=200)
    return format_as_org_momentum(nodes)
```

**What this represents**: If you asked "what has the org been up to lately?",
this is the answer. Recent decisions, recently discovered constraints, recently
evolved patterns. It captures organizational velocity — a team that learned five
things this week has different momentum than one that hasn't evolved in a month.

### Resource Philosophy

Resources project **organizational awareness**, not data. The harness consumes
them as ambient context — "this is what the org looks like right now" — not as
query results. The distinction matters: a query implies the consumer knows what
to ask for. A projection gives the consumer awareness they didn't know they
needed.

Resources are **data** — they expose organizational state. Prompts are
**behavior** — they instruct the harness how to act. A harness may fetch
resources selectively; prompts shape every session.

---

## 3. Prompts

The prompt is the **primary behavior-shaping mechanism**. It is injected into
the host LLM's system context on every session, framing Canon as an intelligent
organizational companion — not a gated write system.

```python
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
```

### Prompt Philosophy

The prompt shapes the harness LLM's behavior around two moments:

1. **Before implementing** — call Canon to get organizational context that might
   affect the approach
2. **At natural checkpoints** — share what was learned so it persists

There are no mechanical flags, confirmation steps, or explicit write gates. The
conversation IS the interface. Canon's orchestrator reasons about whether to
persist based on the content and context of what's shared — the same way a
knowledgeable colleague would decide whether something is worth writing down.

---

## 4. Tools

### `canon`

Single tool for all interactions with the organizational knowledge graph. The
ADK orchestrator determines intent — retrieval, persistence, or both — from the
natural-language `request` parameter.

```python
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
        Agent response with session_id for workflow continuity. The harness
        should extract and pass the session_id on subsequent calls.
    """
    request_ctx = await build_context(ctx)
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

    # Always return session_id so the harness can continue the session
    return f"{response}\n\n---\nsession_id: {resolved_session_id}"
```

### Why a Single Tool

Two tools (`canon_analyze` + `canon_save_memory`) forced the harness LLM to
classify intent before calling Canon. A single `canon` tool delegates that
classification to Canon's ADK orchestrator — which has access to the full
operational knowledge graph and can make richer decisions about how to handle a
request. The orchestrator determines from conversation context whether to
retrieve, persist, or both.

This also means the harness never needs to decide "is this a read or a write?" —
it just talks to Canon naturally. The orchestrator handles the rest.

### Session ID Negotiation

Session continuity between the harness and Canon follows a simple negotiate-on-
first-call pattern:

1. **First call** — the harness omits `session_id`. Canon generates a UUID, uses
   it for the run, and appends it to the response:
   `\n\n---\nsession_id: <uuid>`.
2. **Subsequent calls** — the harness passes the `session_id` it received. Canon
   loads the session's summary for context continuity and echoes the same
   `session_id` back in the response.
3. **New logical task** — the harness omits `session_id` again, starting a fresh
   session.

The negotiation is entirely in-band — no separate handshake endpoint, no
headers. The response always ends with the session_id line. The harness LLM
extracts it because the prompt instructs it to (see §3).

```
┌─────────┐                        ┌───────┐
│ Harness │                        │ Canon │
└────┬────┘                        └───┬───┘
     │  canon(request="...", session_id=None)
     │──────────────────────────────────►│
     │                                   │ generates session_id = uuid4()
     │  "...response...\n---\nsession_id: abc-123"
     │◄──────────────────────────────────│
     │                                   │
     │  canon(request="...", session_id="abc-123")
     │──────────────────────────────────►│
     │                                   │ loads session summary
     │  "...response...\n---\nsession_id: abc-123"
     │◄──────────────────────────────────│
```

---

## 5. ADK Runner Integration

Each tool call invokes the ADK agent. Sessions are identified by `session_id`
for workflow continuity within a logical task, but no server-side state persists
between HTTP requests.

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from canon_mcp.agent import build_orchestrator


async def run_agent(
    tenant_id: str,
    user_id: str,
    session_id: str,
    run_id: str,
    message: str,
    event_feed: "AgentEventFeed",
    db: "AsyncIOMotorDatabase",
) -> str:
    """Invoke the ADK orchestrator agent for a single request lifecycle.

    Constructs a fresh orchestrator per invocation. The session_id provides
    workflow continuity (the ADK agent can reference prior context), but no
    server-side session state persists between HTTP requests.
    """
    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
    if not tenant:
        return "Error: tenant not found."

    # Upsert session document
    session_doc = await db.sessions.find_one_and_update(
        {"sessionId": session_id},
        {
            "$setOnInsert": {
                "tenantId": ObjectId(tenant_id),
                "userId": user_id,
                "sessionId": session_id,
                "status": "active",
                "title": message[:100],
                "summary": None,
                "createdAt": datetime.now(timezone.utc),
            },
            "$inc": {"runCount": 1},
            "$set": {
                "updatedAt": datetime.now(timezone.utc),
                "lastRunAt": datetime.now(timezone.utc),
            },
        },
        upsert=True,
        return_document=True,
    )

    # Retrieve session summary for continuity (None on first run)
    session_summary = session_doc.get("summary")

    orchestrator = build_orchestrator()

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="canon",
        user_id=tenant_id,
        state={
            "app:tenant_id": tenant_id,
            "app:user_id": user_id,
            "app:org_name": tenant["name"],
            "app:session_id": session_id,
            "app:run_id": run_id,
            "app:max_graph_depth": tenant.get("settings", {}).get("maxGraphDepth", 2),
            "app:embedding_model": tenant.get("embeddingModel", "text-embedding-004"),
        },
    )

    from google.adk.apps import App
    from google.adk.apps.context_cache_config import ContextCacheConfig

    canon_app = App(
        name="canon",
        root_agent=orchestrator,
        plugins=[ReasoningFeedPlugin(event_feed)],
        context_cache_config=ContextCacheConfig(
            min_tokens=2048,
            ttl_seconds=1800,
        ),
    )

    runner = Runner(
        app=canon_app,
        session_service=session_service,
    )

    content = Content(
        role="user",
        parts=[Part.from_text(text=_build_message(message, session_summary))],
    )

    # Emit run_started
    await event_feed.broadcast(
        tenant_id=tenant_id,
        session_id=session_id,
        run_id=run_id,
        event={"type": "run_started", "author": "canon_orchestrator", "content": None, "isFinal": False},
    )

    # Run orchestrator — the ReasoningFeedPlugin handles lifecycle events
    # (tool_call_started, tool_call_completed, subagent_invoked) automatically.
    # This loop only needs to detect the final response and reasoning checkpoints.
    final_response = None
    async for event in runner.run_async(
        user_id=tenant_id,
        session_id=session.id,
        new_message=content,
    ):
        # Detect explicit reasoning checkpoints
        if hasattr(event, "function_calls"):
            for fc in event.function_calls:
                if fc.name == "emit_checkpoint":
                    await event_feed.broadcast(
                        tenant_id=tenant_id,
                        session_id=session_id,
                        run_id=run_id,
                        event={
                            "type": "reasoning_checkpoint",
                            "author": "canon_orchestrator",
                            "content": fc.args.get("message", ""),
                            "isFinal": False,
                        },
                    )

        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    # Emit the final response as a visible event for the Reasoning Feed
    if final_response:
        await event_feed.broadcast(
            tenant_id=tenant_id,
            session_id=session_id,
            run_id=run_id,
            event={
                "type": "final_response",
                "author": "canon_orchestrator",
                "content": final_response,
                "isFinal": True,
            },
        )

    # Emit run_completed
    await event_feed.broadcast(
        tenant_id=tenant_id,
        session_id=session_id,
        run_id=run_id,
        event={"type": "run_completed", "author": "canon_orchestrator", "content": None, "isFinal": False},
    )

    # Update session summary for continuity across future runs.
    # Synchronous — blocks the response by ~1-2s. Acceptable for hackathon
    # (single instance, no latency SLA). Production could defer this.
    if final_response:
        updated_summary = await _generate_session_summary(
            previous_summary=session_summary,
            request=message,
            response=final_response,
        )
        await db.sessions.update_one(
            {"sessionId": session_id},
            {"$set": {"summary": updated_summary}},
        )

    return final_response or "No response generated."


def _build_message(request: str, session_summary: str | None) -> str:
    """Construct the message sent to the orchestrator, with session context if available.

    The summary is injected as a brief orienting preamble — not as authoritative
    context. The orchestrator's primary context comes from retrieval and graph
    traversal, not from the summary. Keep injection minimal to preserve context
    budget for organizational knowledge.
    """
    if session_summary:
        return f"[Prior session context: {session_summary}]\n\nRequest:\n{request}"
    return f"Request:\n{request}"


async def _generate_session_summary(
    previous_summary: str | None,
    request: str,
    response: str,
) -> str:
    """Generate a rolling semantic summary of the session's evolving context.

    Uses FAST_MODEL for cost-efficiency — this is a compression task, not reasoning.
    The summary captures what was discussed, decided, and written — enough to
    orient the orchestrator on subsequent runs without replaying full history.

    Aggressively concise: the orchestrator's context budget is shared with
    retrieval results and graph traversals. Every token in the summary competes
    with organizational knowledge that could be surfaced.
    """
    import google.genai as genai

    prompt = f"""\
Produce an aggressively concise semantic summary (2-3 sentences max) of this session.
Capture ONLY: key decisions made, memory nodes written, and open threads that affect the next run.
Omit pleasantries, reasoning process, and anything retrievable from the knowledge graph.

{"Previous summary: " + previous_summary if previous_summary else "This is the first run in this session."}

Latest request: {request[:500]}
Latest response: {response[:1000]}

Write only the updated summary — no preamble, no explanation. Ruthlessly compress."""

    client = genai.Client()
    result = await client.aio.models.generate_content(
        model=f"models/{FAST_MODEL}",
        contents=prompt,
    )
    return result.text.strip()
```

### Why Ephemeral ADK Sessions

The ADK `Runner` requires a session service. By creating
`InMemorySessionService` per request, we get:

- **Stateless scaling** — Cloud Run needs no affinity
- **Isolation** — No cross-request contamination
- **Simplicity** — No session cleanup, no state management

Continuity across runs is provided by the session's `summary` field in MongoDB —
a lightweight semantic context that the orchestrator receives at the start of
each run. The ADK session is ephemeral; the _workflow_ session persists in
MongoDB with its rolling summary.

---

## 6. Reasoning Feed (Event Streaming)

The Reasoning Feed UI observes Canon's reasoning in real time via Server-Sent
Events. This is **observability only** — the engineer watches but never acts
through it.

### AgentEventFeed

```python
from asyncio import Queue
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from canon_mcp.repositories import AgentEventRepository


class AgentEventFeed:
    """Manages live event streaming and persistence for the Reasoning Feed.

    Assigns sequence numbers and timestamps centrally — callers provide
    type, author, content, and isFinal. This ensures globally ordered events
    regardless of whether they originate from the ReasoningFeedPlugin or the
    runner event loop.
    """

    def __init__(self, event_repo: AgentEventRepository):
        self._subscribers: dict[str, list[Queue]] = {}
        self._event_repo = event_repo
        self._sequences: dict[str, int] = {}  # run_id → current sequence

    async def broadcast(self, tenant_id: str, session_id: str, run_id: str, event: dict) -> None:
        """Broadcast an event to subscribers and persist to agent_events.

        Assigns sequence number and timestamp if not already present.
        """
        # Assign sequence (monotonically increasing per run)
        seq = self._sequences.get(run_id, 0) + 1
        self._sequences[run_id] = seq
        event.setdefault("sequence", seq)
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        # Persist for replay
        await self._event_repo.insert(
            tenant_id=tenant_id,
            session_id=session_id,
            run_id=run_id,
            event=event,
        )

        # Fan out to live subscribers
        key = f"{tenant_id}:{session_id}"
        for queue in self._subscribers.get(key, []):
            await queue.put(event)

    async def subscribe(self, tenant_id: str, session_id: str) -> AsyncIterator[dict]:
        """Subscribe to live events for a session."""
        key = f"{tenant_id}:{session_id}"
        queue: Queue = Queue()

        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(queue)

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers[key].remove(queue)
            if not self._subscribers[key]:
                del self._subscribers[key]

    async def replay(self, tenant_id: str, session_id: str, after_sequence: int = 0) -> list[dict]:
        """Replay stored events from a sequence number."""
        return await self._event_repo.list_after(
            tenant_id=tenant_id,
            session_id=session_id,
            after_sequence=after_sequence,
        )
```

### SSE Endpoint (Replay + Live Stream)

The SSE endpoint first replays stored events, then continues with live
streaming. Supports `Last-Event-ID` for reconnection.

```python
from fastapi.responses import StreamingResponse
from fastapi import Depends
from dependencies import jwt_auth, api_token_auth, get_event_feed
import json


async def session_event_stream(
    session_id: str,
    after: int = 0,
    user: dict = Depends(jwt_auth),
    event_feed=Depends(get_event_feed),
):
    """SSE endpoint for the Reasoning Feed UI.

    1. Replays stored events from agent_events collection
    2. Continues streaming live events
    3. Supports `after` query param for reconnection

    Frontend mount uses JWT via Authorization header (proxied by Next.js route handler).
    Harness mount uses API token auth with a separate router endpoint.
    """
    tenant_id = user["tenantId"]

    # Support reconnection via `after` query param
    after_sequence = after

    async def event_stream():
        # Phase 1: Replay stored events
        stored = await event_feed.replay(tenant_id, session_id, after_sequence)
        for evt in stored:
            event_id = evt.get("sequence", 0)
            yield f"id: {event_id}\ndata: {json.dumps(evt)}\n\n"

        # Phase 2: Stream live events
        async for evt in event_feed.subscribe(tenant_id, session_id):
            event_id = evt.get("sequence", 0)
            yield f"id: {event_id}\ndata: {json.dumps(evt)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### Event Lifecycle

1. Harness calls `canon` tool
2. ADK runner invokes the orchestrator, which delegates to subagents
3. Each event is broadcast via `AgentEventFeed` — persisted and fanned out to
   subscribers
4. Reasoning Feed UI renders the multi-agent reasoning trace in real time
5. Tool call returns final response to harness independently

The SSE endpoint has no influence on tool execution. If no clients are
connected, events are still persisted for later replay.

> **Implementation note (race condition avoidance):** The correct
> subscribe-first pattern is: (1) subscribe to the live event queue, (2) replay
> stored events from `agent_events`, (3) drain the live queue with dedup by
> `sequence`. This ensures no events are lost between replay and live
> subscription. The current implementation approximates this by replaying first
> then subscribing — acceptable for single-instance hackathon deployment, but
> production should adopt subscribe-first with sequence-based dedup.

### Scaling Limitation

The in-process subscriber dict broadcasts events within a single Cloud Run
instance. With `max_instances=1` (hackathon constraint), this is sufficient.
Production deployments would introduce a pub/sub intermediary (Redis, Cloud
Pub/Sub) for cross-instance fan-out.

---

## 7. Dependency Injection & Tenant Resolution

### Service Classes

Injectable service classes that are explicit and testable. Single database — all
collections (`memory_nodes`, `sessions`, `agent_events`, `tenants`,
`api_tokens`) live in the same `canon` database.

```python
from dataclasses import dataclass
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from hashlib import sha256


class MongoProvider:
    """Provides database connection."""

    def __init__(self, uri: str | None = None):
        self._uri = uri or os.environ["MONGODB_URI"]
        self._client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        self._client = AsyncIOMotorClient(self._uri)

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._client["canon"]


class TenantResolver:
    """Resolves tenant identity from authentication tokens."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    async def resolve(self, auth_header: str) -> "TenantContext | None":
        """Resolve a Bearer token to a TenantContext."""
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]
        token_hash = sha256(token.encode()).hexdigest()
        record = await self._db.api_tokens.find_one({"token": token_hash})

        if not record:
            return None

        await self._db.api_tokens.update_one(
            {"_id": record["_id"]},
            {"$set": {"lastUsedAt": datetime.now(timezone.utc)}},
        )

        return TenantContext(
            tenant_id=str(record["tenantId"]),
            user_id=str(record.get("userId", record["tenantId"])),
        )

    async def resolve_token(self, raw_token: str) -> "TenantContext | None":
        """Resolve a raw token string (for SSE query-param auth)."""
        token_hash = sha256(raw_token.encode()).hexdigest()
        record = await self._db.api_tokens.find_one({"token": token_hash})
        if not record:
            return None
        return TenantContext(
            tenant_id=str(record["tenantId"]),
            user_id=str(record.get("userId", record["tenantId"])),
        )


@dataclass
class TenantContext:
    """Resolved tenant identity."""
    tenant_id: str
    user_id: str


@dataclass
class RequestContext:
    """Request-scoped dependency container."""
    tenant_id: str
    user_id: str
    session_id: str | None
    run_id: str | None
    db: AsyncIOMotorDatabase
    event_feed: AgentEventFeed
```

### Auth Strategy

Authentication uses **FastAPI dependency injection** — each route declares its
auth dependency via `Depends()`. No middleware classes, no path inspection.

| Route group                        | Auth dependency       | Tenant source |
| ---------------------------------- | --------------------- | ------------- |
| `/mcp`                             | FastMCP's own auth    | Path param    |
| `/api/v1/tenants/{id}/sessions/...`| `api_token_auth`      | Path param    |
| `/api/v1/auth/register`, `/login`  | None (public)         | —             |
| `/api/v1/sessions/...`, `/graph`   | `jwt_auth`            | JWT claim     |
| `/api/v1/teams/...`               | `jwt_auth`            | JWT claim     |

Public routes (`/register`, `/login`, `/health`) omit the auth dependency
entirely. Protected routes declare `user: dict = Depends(jwt_auth)` or
`ctx: TenantContext = Depends(api_token_auth)` — the dependency raises
`HTTPException(401)` if auth fails.

### Token Storage

Tokens are stored as SHA-256 hashes. The raw token is shown to the engineer
exactly once at registration:

```python
import secrets

raw_token = f"ct_{secrets.token_urlsafe(32)}"
token_hash = sha256(raw_token.encode()).hexdigest()
db.api_tokens.insert_one({
    "tenantId": tenant_id,
    "token": token_hash,
    "label": "Initial setup token",
    "createdAt": datetime.now(timezone.utc),
    "lastUsedAt": None,
})
# Return raw_token to user — never stored again
```

### Harness Configuration

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "canon": {
      "url": "https://canon-<project>.run.app/mcp/mcp",
      "headers": {
        "Authorization": "Bearer ct_<token>"
      }
    }
  }
}
```

**Claude Code** (`.mcp.json`):

```json
{
  "mcpServers": {
    "canon": {
      "url": "https://canon-<project>.run.app/mcp/mcp",
      "headers": {
        "Authorization": "Bearer ct_<token>"
      }
    }
  }
}
```

### Flow Summary

1. Engineer registers org via Reasoning Feed UI → receives `ct_...` token (shown
   once)
2. Token placed in harness config as Bearer header
3. On each request: `api_token_auth` dependency uses `TenantResolver` →
   resolves `TenantContext`
4. Tool/resource handlers access resolved tenant via `build_context(ctx)`

### `build_context` — Bridge Between FastMCP and FastAPI

FastMCP tool/resource handlers receive a `Context` object that wraps the MCP
protocol session. To access tenant state, `build_context` bridges the two by
using the same auth resolution logic as the FastAPI dependencies:

```python
async def build_context(ctx: Context) -> RequestContext:
    """Extract tenant context from the MCP request's underlying HTTP transport.

    FastMCP's Context provides access to the underlying transport request.
    The API token has already been validated by FastMCP's own auth — this
    function resolves the tenant from the token.
    """
    # FastMCP exposes the transport-level request via ctx
    request = ctx.request  # Transport-level HTTP request
    db = request.app.state.mongo.db

    # Resolve tenant from API token (same logic as api_token_auth dependency)
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    resolver = TenantResolver(db)
    tenant_ctx = await resolver.resolve(token)

    return RequestContext(
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        session_id=None,
        run_id=None,
        db=db,
        event_feed=request.app.state.event_feed,
    )
```

---

## 8. Frontend-Facing API

These routes serve the Next.js frontend. Authenticated via JWT (issued by
`/api/v1/auth/login`). The frontend never connects to MongoDB directly — all
data flows through these endpoints.

Handler implementations live in their respective router modules
(`routers/auth.py`, `routers/teams.py`, `routers/graph.py`). JWT
helpers live in `services/jwt.py`.

### Auth Router (`routers/auth.py`)

```python
import bcrypt
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, EmailStr
from fastapi import Depends, HTTPException
from dependencies import jwt_auth, get_db


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


async def register(body: RegisterRequest, db=Depends(get_db)):
    """POST /api/v1/auth/register — Create account, return JWT."""
    email = body.email.strip().lower()
    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    user = {
        "email": email,
        "name": body.name,
        "passwordHash": password_hash,
        "tenantId": None,
        "role": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }

    try:
        result = await db.users.insert_one(user)
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail="Email already registered")
        raise

    token = _issue_jwt(str(result.inserted_id), email, body.name, None, None)
    return {"token": token, "user": {"email": email, "name": body.name, "tenantId": None}}


async def login(body: LoginRequest, db=Depends(get_db)):
    """POST /api/v1/auth/login — Validate credentials, return JWT."""
    user = await db.users.find_one({"email": body.email.strip().lower()})
    if not user or not bcrypt.checkpw(body.password.encode(), user["passwordHash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _issue_jwt(
        str(user["_id"]), user["email"], user["name"],
        str(user["tenantId"]) if user.get("tenantId") else None,
        user.get("role"),
    )
    return {
        "token": token,
        "user": {
            "email": user["email"],
            "name": user["name"],
            "tenantId": str(user["tenantId"]) if user.get("tenantId") else None,
            "role": user.get("role"),
        },
    }


async def me(user: dict = Depends(jwt_auth)):
    """GET /api/v1/auth/me — Current user from JWT."""
    return {
        "userId": user["sub"],
        "email": user["email"],
        "name": user["name"],
        "tenantId": user.get("tenantId"),
        "role": user.get("role"),
    }


def _issue_jwt(user_id, email, name, tenant_id, role) -> str:
    return pyjwt.encode(
        {
            "sub": user_id,
            "email": email,
            "name": name,
            "tenantId": tenant_id,
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
```

### Teams Router (`routers/teams.py`)

```python
import secrets
from pydantic import BaseModel
from fastapi import Depends, HTTPException
from dependencies import jwt_auth, get_db


class CreateTeamRequest(BaseModel):
    name: str


class JoinTeamRequest(BaseModel):
    code: str


class CreateTokenRequest(BaseModel):
    label: str = "API token"


async def create_team(body: CreateTeamRequest, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """POST /api/v1/teams/create — Create team, assign user as owner, generate API token."""
    tenant = {
        "name": body.name,
        "slug": body.name.lower().replace(" ", "-"),
        "createdAt": datetime.now(timezone.utc),
        "settings": {"maxGraphDepth": 2},
    }
    result = await db.tenants.insert_one(tenant)
    tenant_id = result.inserted_id

    # Assign user to tenant as owner
    await db.users.update_one(
        {"_id": ObjectId(user["sub"])},
        {"$set": {"tenantId": tenant_id, "role": "owner", "updatedAt": datetime.now(timezone.utc)}},
    )

    # Generate default harness API token
    raw_token = f"ct_{secrets.token_urlsafe(32)}"
    token_hash = sha256(raw_token.encode()).hexdigest()
    await db.api_tokens.insert_one({
        "tenantId": tenant_id,
        "userId": user["sub"],
        "token": token_hash,
        "label": "Default setup token",
        "createdAt": datetime.now(timezone.utc),
        "lastUsedAt": None,
    })

    # Re-issue JWT with tenantId
    new_jwt = _issue_jwt(user["sub"], user["email"], user["name"], str(tenant_id), "owner")

    return {
        "token": new_jwt,
        "tenant": {"id": str(tenant_id), "name": body.name},
        "apiToken": raw_token,  # Shown once
    }


async def join_team(body: JoinTeamRequest, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """POST /api/v1/teams/join — Join team via invite code."""
    code = body.code.strip().upper()
    invite = await db.invites.find_one({
        "code": code,
        "usesRemaining": {"$gt": 0},
        "expiresAt": {"$gt": datetime.now(timezone.utc)},
    })
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invite code")

    tenant_id = invite["tenantId"]
    await db.users.update_one(
        {"_id": ObjectId(user["sub"])},
        {"$set": {"tenantId": tenant_id, "role": "member", "updatedAt": datetime.now(timezone.utc)}},
    )
    await db.invites.update_one({"_id": invite["_id"]}, {"$inc": {"usesRemaining": -1}})

    tenant = await db.tenants.find_one({"_id": tenant_id})
    new_jwt = _issue_jwt(user["sub"], user["email"], user["name"], str(tenant_id), "member")

    return {
        "token": new_jwt,
        "tenant": {"id": str(tenant_id), "name": tenant["name"]},
    }


async def create_invite(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """POST /api/v1/teams/invite — Generate invite code (owner only)."""
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can create invites")

    code = secrets.token_hex(4).upper()  # 8-char hex

    await db.invites.insert_one({
        "tenantId": ObjectId(user["tenantId"]),
        "code": code,
        "createdBy": ObjectId(user["sub"]),
        "usesRemaining": 10,
        "expiresAt": datetime.now(timezone.utc) + timedelta(days=7),
        "createdAt": datetime.now(timezone.utc),
    })

    return {"code": code}


async def list_tokens(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """GET /api/v1/teams/tokens — List API tokens for tenant."""
    tokens = await db.api_tokens.find(
        {"tenantId": ObjectId(user["tenantId"])},
        {"token": 0},  # Never return the hash
    ).sort("createdAt", -1).to_list(length=50)

    return [{
        "id": str(t["_id"]),
        "label": t["label"],
        "createdAt": t["createdAt"].isoformat(),
        "lastUsedAt": t["lastUsedAt"].isoformat() if t.get("lastUsedAt") else None,
    } for t in tokens]


async def create_token(body: CreateTokenRequest, user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """POST /api/v1/teams/tokens — Create new API token."""
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can create tokens")

    raw_token = f"ct_{secrets.token_urlsafe(32)}"
    token_hash = sha256(raw_token.encode()).hexdigest()

    await db.api_tokens.insert_one({
        "tenantId": ObjectId(user["tenantId"]),
        "userId": user["sub"],
        "token": token_hash,
        "label": body.label,
        "createdAt": datetime.now(timezone.utc),
        "lastUsedAt": None,
    })

    return {"token": raw_token}  # Shown once
```

### Graph Router (`routers/graph.py`)

```python
from fastapi import Depends
from dependencies import jwt_auth, get_db


async def get_graph(user: dict = Depends(jwt_auth), db=Depends(get_db)):
    """GET /api/v1/graph — Full memory graph for visualization."""
    tenant_id = user["tenantId"]

    nodes = await db.memory_nodes.find(
        {"tenantId": ObjectId(tenant_id)},
        {
            "embedding": 0,
            "content": 0,  # Exclude large fields
        },
    ).to_list(length=2000)

    # Transform to graph format
    graph_nodes = []
    graph_links = []
    node_ids = {str(n["_id"]) for n in nodes}

    for node in nodes:
        nid = str(node["_id"])
        graph_nodes.append({
            "id": nid,
            "name": node["name"],
            "description": node.get("description", ""),
            "status": node.get("status", ""),
            "tags": node.get("tags", []),
            "supersedes": str(node["supersedes"]) if node.get("supersedes") else None,
            "supersededBy": str(node["supersededBy"]) if node.get("supersededBy") else None,
            "updatedAt": node["updatedAt"].isoformat(),
            "createdAt": node["createdAt"].isoformat(),
        })

        # Related edges (deduplicated)
        for rel_id in node.get("relatedEntityIds", []):
            rid = str(rel_id)
            if rid in node_ids and nid < rid:  # Dedup: lexicographic smaller as source
                graph_links.append({"source": nid, "target": rid, "type": "related"})

        # Supersession edge
        if node.get("supersedes"):
            sid = str(node["supersedes"])
            if sid in node_ids:
                graph_links.append({"source": sid, "target": nid, "type": "supersedes"})

    return {"nodes": graph_nodes, "links": graph_links}
```
