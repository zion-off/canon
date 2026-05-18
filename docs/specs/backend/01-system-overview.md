# 01 — System Overview

## System Purpose

Canon is an organizational continuity layer. It gives coding assistants
persistent, semantically interpreted awareness of how an engineering
organization actually works — its decisions, patterns, migrations, ownership
boundaries, architectural constraints, and operational realities.

Where coding assistants have session memory that evaporates, Canon provides
ambient organizational cognition: a persistent reasoning substrate that any
compatible harness (Cursor, Claude Code, Gemini CLI) can invoke through a single
MCP tool. Behind this interface, an ADK agent system reasons over the
organization's operational knowledge graph — a living semantic structure in
MongoDB Atlas where nodes represent organizational knowledge and edges encode
the relationships between them.

Canon is not a lookup service. It is not an enterprise workflow engine,
governance platform, or lifecycle-managed records database. Each invocation
triggers genuine organizational reasoning: the agent interprets context,
traverses semantic relationships, synthesizes understanding from multiple
knowledge domains, and returns insight that reflects how the organization
actually operates. When engineers surface new knowledge, the agent structures it
into the graph conversationally — no gates, no confirmation flows, no
bureaucracy.

Persistence is conversational and transparent. Memory emerges from dialogue
between engineer and agent, with every reasoning step, retrieval decision, and
write action visible in the Reasoning Feed. There are no hidden mechanisms. The
agent's entire cognitive process — what it searched, what it found, what it
concluded, what it wrote — is legible, inspectable, and replayable.

---

## Architectural Layers

Canon separates into four layers, each independently deployable and testable.

### Layer 1 — MCP Transport

| Attribute      | Value                                                                                                    |
| -------------- | -------------------------------------------------------------------------------------------------------- |
| Runtime        | Python 3.14, Cloud Run                                                                                   |
| Framework      | FastMCP + Starlette                                                                                      |
| Protocol       | MCP over streamable HTTP                                                                                 |
| Responsibility | Authenticate requests, resolve tenant + user, invoke ADK agent, stream reasoning events, return response |

The MCP server is the system's sole public interface. A single `canon` tool
accepts a request and optional context. The orchestrator determines intent —
retrieve, remember, or both — from the semantic content of the request itself.
There is no routing logic in the transport layer.

Each tool call is a single HTTP request: the agent reasons, the reasoning
streams through SSE, the response returns, and the request completes. Stateless
per invocation.

```python
from fastmcp import FastMCP

mcp = FastMCP("Canon")

@mcp.tool("canon")
async def canon(
    request: str,
    context: str = "",
    session_id: str | None = None,
    ctx: Context = None,
) -> str:
    """
    Interact with organizational memory. Ask questions about how the
    organization works, or share knowledge worth remembering.

    Args:
        request: What you want to know or what the organization should remember.
        context: Optional surrounding context (current file, recent conversation, task).
        session_id: Optional session to continue. Omit to start a new reasoning session.
    """
    # Tenant resolved by middleware, injected via build_context (see Doc 04 §7)
    request_ctx = await build_context(ctx)
    tenant_id = request_ctx.tenant_id
    user_id = request_ctx.user_id

    run_id = str(uuid4())
    session_id = session_id or str(uuid4())

    orchestrator = build_orchestrator()
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="canon",
        user_id=tenant_id,
        state={
            "app:tenant_id": tenant_id,
            "app:user_id": user_id,
        },
    )

    canon_app = App(
        name="canon",
        root_agent=orchestrator,
        plugins=[ReasoningFeedPlugin(event_feed)],
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800),
    )

    runner = Runner(
        app=canon_app, session_service=session_service
    )
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=_build_message(
            f"Request:\n{request}\n\nContext:\n{context}", session_summary
        ))]
    )

    events = []
    async for event in runner.run_async(
        user_id=tenant_id, session_id=session.id, new_message=message
    ):
        await event_feed.broadcast(tenant_id, session_id, run_id, event)
        events.append(event)

    response = extract_final_response(events)
    # Always return session_id so the harness can continue the session
    return f"{response}\n\n---\nsession_id: {session_id}"
```

No `confirmed` parameter. No write gate. The orchestrator is intelligent enough
to determine when persistence is appropriate from the request semantics alone.
The harness receives `session_id` in every response and passes it back on
subsequent calls for workflow continuity (see Doc 04 §4).

### Layer 2 — ADK Agent System

| Attribute      | Value                                                                                                                                                             |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Models         | `REASONING_MODEL` (orchestrator, memory_writer), `FAST_MODEL` (semantic_retriever, graph_explorer). Capability-tier constants backed by env vars — see Doc 03 §2. |
| Framework      | Google ADK (`LlmAgent` orchestrator, `AgentTool`, `Agent`)                                                                                                        |
| Responsibility | Organizational reasoning: semantic interpretation, graph-native retrieval, conflict analysis, synthesis, memory structuring                                       |

The ADK agent system is the reasoning core. A Gemini 3.1 Pro `LlmAgent`
orchestrator receives each request, interprets organizational intent, and
delegates to three focused subagents. The orchestrator **is** the intelligence —
conflict analysis, synthesis, organizational reasoning all live in the
orchestrator's reasoning. Subagents are capability providers, not
decision-makers. A `ReasoningFeedPlugin` intercepts all lifecycle events (tool
calls, agent delegations, model interactions) and emits them to the Reasoning
Feed automatically.

```python
from google.adk.agents import Agent
from google.adk.tools import AgentTool, google_search

semantic_retriever = Agent(
    name="semantic_retriever",
    model=FAST_MODEL,
    instruction=SEMANTIC_RETRIEVER_INSTRUCTION,
    output_key="retrieval_results",
    tools=[...],  # MongoDB hybrid search tools
)

graph_explorer = Agent(
    name="graph_explorer",
    model=FAST_MODEL,
    instruction=GRAPH_EXPLORER_INSTRUCTION,
    output_key="graph_results",
    tools=[...],  # MongoDB $graphLookup tools
)

memory_writer = Agent(
    name="memory_writer",
    model=REASONING_MODEL,
    instruction=MEMORY_WRITER_INSTRUCTION,
    output_key="write_result",
    output_schema=MemoryNodeOutput,  # Pydantic model for type-safe output
    tools=[...],  # MongoDB write + embedding tools
)

def build_orchestrator() -> Agent:
    return Agent(
        name="canon_orchestrator",
        model=REASONING_MODEL,
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            AgentTool(semantic_retriever),
            AgentTool(graph_explorer),
            AgentTool(memory_writer),
            google_search,            # live internet grounding for enrichment
            emit_checkpoint_tool,     # explicit reasoning milestones
        ],
    )
```

**Three subagents — each a distinct cognitive capability:**

| Subagent             | Purpose                             | Access Pattern                                                       |
| -------------------- | ----------------------------------- | -------------------------------------------------------------------- |
| `semantic_retriever` | Find knowledge by meaning           | `$vectorSearch` + `$search` via `$rankFusion` hybrid pipeline        |
| `graph_explorer`     | Find knowledge by connection        | `$graphLookup` traversal across `relatedEntityIds` edges             |
| `memory_writer`      | Structure and persist new knowledge | Insert node, resolve relationships, generate embedding synchronously |

The orchestrator decides what to invoke, in what order, based on what it judges
necessary. The sequence of delegations emerges from reasoning, not from control
flow. A single request might trigger retrieval alone, retrieval then write, or
write alone — the orchestrator determines this from organizational context.

**Decision checkpoints** — explicit reasoning milestones emitted by the
orchestrator:

| Checkpoint Example                                                                 | What It Communicates                      |
| ---------------------------------------------------------------------------------- | ----------------------------------------- |
| "Searching organizational memory for payment service context"                      | Agent is gathering context                |
| "Found migration dependency chain. Traversing graph for affected services."        | Agent is following semantic relationships |
| "Existing node describes earlier JWT decision. Synthesizing with new information." | Agent is performing conflict analysis     |
| "Structuring memory: auth-service-jwt-rotation with 3 resolved relationships"      | Agent is persisting knowledge             |

### Layer 3 — Reasoning Feed

| Attribute      | Value                                                                  |
| -------------- | ---------------------------------------------------------------------- |
| Transport      | Server-Sent Events (SSE)                                               |
| Storage        | `agent_events` collection in MongoDB Atlas                             |
| Responsibility | Make the agent's cognitive process visible, structured, and replayable |

The Reasoning Feed is not telemetry. It is an organizational reasoning interface
that makes the agent's cognitive process legible to engineers. Every retrieval,
every graph traversal, every synthesis decision, every write — visible,
structured, replayable.

The `ReasoningFeedPlugin` (Doc 03 §8) automatically captures tool calls,
subagent invocations, and model interactions. Explicit `emit_checkpoint` calls
add orchestrator-level reasoning milestones that the plugin cannot infer.
Together they produce a complete cognitive trace.

Events are stored in `agent_events` and streamed live via SSE. Late-joining
clients hydrate from stored events then continue streaming.

```python
await event_feed.broadcast(
    tenant_id=tenant_id,
    session_id=session_id,
    run_id=run_id,
    event={
        "type": "reasoning_checkpoint",
        "content": "Found migration dependency chain. Traversing graph for affected services.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence,
    }
)
```

**Event types:**

| Event Type             | Rendering                                             |
| ---------------------- | ----------------------------------------------------- |
| `reasoning_checkpoint` | Highlighted milestone card                            |
| `tool_call_started`    | "Querying: ownership boundaries for payments service" |
| `tool_call_completed`  | Retrieved document summaries (collapsed)              |
| `subagent_invoked`     | "semantic_retriever started"                          |
| `run_started`          | Session run initiation marker                         |
| `final_response`       | Canon's synthesized answer — emphasized block         |
| `run_completed`        | Completed reasoning panel                             |

**Session replay:**

```
1. GET /api/v1/tenants/{tenant_id}/sessions/{session_id}/events  → stored events
2. GET /api/v1/tenants/{tenant_id}/sessions/{session_id}/stream  → live SSE
```

### Layer 4 — Organizational Memory (MongoDB Atlas)

| Attribute      | Value                                              |
| -------------- | -------------------------------------------------- |
| Service        | MongoDB Atlas (M10+ for Vector Search)             |
| Database       | `canon` (single database)                          |
| Access         | MongoDB MCP Server (subprocess, stdio)             |
| Responsibility | Store and retrieve the operational knowledge graph |

MongoDB Atlas holds the operational knowledge graph. A single `canon` database
contains all collections. Documents in `memory_nodes` represent organizational
knowledge — decisions, patterns, ownership boundaries, conventions, migrations,
incidents, architectural constraints. Each node connects to others through
`relatedEntityIds`, forming a traversable semantic graph.

Atlas Vector Search enables semantic retrieval (finding knowledge by meaning).
`$graphLookup` enables relationship traversal (finding knowledge by connection).
Together they give the agent two complementary modes of organizational
reasoning.

**Collections:**

| Collection     | Purpose                                                                                |
| -------------- | -------------------------------------------------------------------------------------- |
| `memory_nodes` | Operational knowledge graph. Polymorphic documents with semantic edges and embeddings. |
| `agent_events` | Reasoning traces per invocation. Powers Reasoning Feed replay.                         |
| `sessions`     | Workflow session groups. Tenant + user scoped.                                         |
| `api_tokens`   | Harness authentication tokens. Lookup: token → tenant.                                 |
| `tenants`      | Tenant configuration and metadata.                                                     |

Embeddings are generated synchronously during writes by the `memory_writer`
subagent. No queue, no async pipeline — the embedding exists on the node at
write time.

---

## Data Flow

### Session Model

| Concept      | Scope                             | Lifecycle                                                                 |
| ------------ | --------------------------------- | ------------------------------------------------------------------------- |
| `session_id` | UI/workflow grouping              | Spans multiple `canon` invocations; harness can pass existing or get new  |
| `run_id`     | One execution of the `canon` tool | Created per request; events stored per run within a session               |
| `summary`    | Rolling semantic context          | Updated after each run; injected into the next run's orchestrator context |

**Session continuity:** Each run is stateless — no in-memory state persists
between requests. But sessions carry a `summary` field: a rolling semantic
summary (2–5 sentences) that captures what was discussed, decided, and written.
On subsequent runs within the same session, this summary is injected into the
orchestrator's context, giving it awareness of prior conversation without
replaying full history. The summary is generated post-run by `FAST_MODEL` (a
compression task, not reasoning). Organizational memory itself lives in
`memory_nodes` and the graph — the session summary is purely a continuity hint.

### Single Tool Flow

Every interaction — read, write, or both — enters through the same `canon` tool.
The orchestrator determines what happens next.

```
Engineer's harness calls canon(request, context)
    │
    ▼
┌─ Layer 1: MCP Transport (Cloud Run) ─────────────────────────────┐
│                                                                    │
│  1. Resolve tenant_id + user_id from auth token                    │
│  2. Assign run_id; resolve or create session_id                    │
│  3. Build orchestrator with 3 subagents                            │
│                                                                    │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌─ Layer 2: ADK Agent System ───────────────────────────────────────┐
│                                                                    │
│  Orchestrator (Gemini 3.1 Pro) reasons about intent:               │
│                                                                    │
│  ┌─ READ PATH ──────────────────────────────────────────────────┐  │
│  │  Checkpoint: "Searching organizational memory for X"          │  │
│  │  → semantic_retriever: hybrid search ($rankFusion)            │  │
│  │  Checkpoint: "Found 3 nodes. Exploring graph."                │  │
│  │  → graph_explorer: $graphLookup traversal                     │  │
│  │  Checkpoint: "Synthesizing organizational context."           │  │
│  │  → Orchestrator synthesizes response                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─ WRITE PATH ─────────────────────────────────────────────────┐  │
│  │  Checkpoint: "Interpreting as organizational memory."          │  │
│  │  → semantic_retriever: find related existing nodes             │  │
│  │  Checkpoint: "Found 2 related nodes. Structuring memory."     │  │
│  │  → memory_writer: structure node, resolve relationships,      │  │
│  │    generate embedding synchronously, persist                   │  │
│  │  Checkpoint: "Persisted: auth-service-jwt-rotation"           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────┬───────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
┌─ Layer 3 ────────┐  ┌─ Layer 4 ──────┐  ┌─ Response ────────────┐
│ Reasoning Feed    │  │ MongoDB Atlas  │  │ Return to harness     │
│ SSE broadcast +   │  │ Read/write     │  │                       │
│ agent_events      │  │ memory_nodes   │  │                       │
│ store             │  │                │  │                       │
└───────────────────┘  └────────────────┘  └───────────────────────┘
```

The orchestrator may invoke both paths in a single request — retrieve context,
then persist new knowledge informed by what it found. The boundary between read
and write is a reasoning decision, not a structural one.

---

## Multi-tenancy & Identity

Isolation is row-level, enforced at the data layer. All operations — reads,
writes, reasoning events — are scoped to tenant + user.

```python
class TenantResolver:
    """Resolves tenantId and userId from auth token. See Doc 04 §7 for full implementation."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db  # Single canon database

    async def resolve(self, auth_header: str) -> "TenantContext | None":
        token = auth_header.removeprefix("Bearer ")
        token_hash = sha256(token.encode()).hexdigest()
        record = await self._db.api_tokens.find_one({"token": token_hash})
        if not record:
            return None
        return TenantContext(
            tenant_id=str(record["tenantId"]),
            user_id=str(record.get("userId", record["tenantId"])),
        )
```

Every document includes `tenantId`. All queries are scoped:

```javascript
// Compound indexes lead with tenantId
{ tenantId: 1, userId: 1, updatedAt: -1 }

// agent_events index
{ tenantId: 1, sessionId: 1, sequence: 1 }

// Vector search pre-filters on tenantId
{
  $vectorSearch: {
    queryVector: embedding,
    path: "embedding",
    filter: { tenantId: ObjectId("665a0000000000000000000a") },
    numCandidates: 100,
    limit: 10
  }
}
```

---

## Deployment Topology

```
┌────────────────────────────────────────────────────────────────────┐
│  Google Cloud Run (max_instances: 1 — hackathon constraint*)       │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Canon MCP Server (FastMCP + Starlette, Python 3.14)         │  │
│  │  - POST /mcp — single `canon` tool call from harnesses       │  │
│  │  - GET /api/v1/tenants/{id}/sessions/{id}/stream — SSE       │  │
│  │  - GET /api/v1/tenants/{id}/sessions — list sessions         │  │
│  │  - Runs ADK Runner in-process per request                    │  │
│  │  - Spawns MongoDB MCP Server subprocesses (stdio)            │  │
│  │  - In-memory SSE broadcast (single instance)                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
          │                              │
          │ MongoDB Wire Protocol        │ SSE
          ▼                              ▼
┌───────────────────────────────┐  ┌──────────────────────────────┐
│  MongoDB Atlas (M10+)         │  │  Reasoning Feed UI           │
│                               │  │  (Next.js on Vercel)         │
│  canon database:              │  │                              │
│  - memory_nodes               │  │  - Session replay            │
│  - agent_events               │  │  - Live SSE streaming        │
│  - sessions                   │  │  - Decision checkpoint cards │
│  - api_tokens                 │  │  - Org registration          │
│  - tenants                    │  │  - Token management          │
│  - Vector Search indexes      │  │  - Reasoning visibility      │
│  - Atlas Search indexes       │  │                              │
└───────────────────────────────┘  └──────────────────────────────┘
```

**\*Hackathon constraint:** `max_instances: 1` simplifies the demo by enabling
in-memory SSE broadcast without a pub/sub intermediary. In production, this
would change to:

- Remove `max_instances` cap (allow auto-scaling)
- Add Redis or Cloud Pub/Sub for cross-instance event fan-out
- Use sticky sessions or client-side reconnection with event replay from
  `agent_events`

---

## Technology Stack

| Technology              | Role                                                                                                                                                                   |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Google ADK**          | Agent orchestration — LlmAgent with AgentTool subagent delegation, McpToolset for MongoDB MCP, BasePlugin for Reasoning Feed, ContextCacheConfig for latency reduction |
| **Gemini 3.1 Pro**      | Orchestrator and memory_writer reasoning (`REASONING_MODEL`)                                                                                                           |
| **Gemini 3.1 Flash**    | Subagent execution — retrieval and graph exploration (`FAST_MODEL`)                                                                                                    |
| **MongoDB Atlas**       | Organizational memory — vector search + full-text + graph traversal in one engine                                                                                      |
| **MongoDB MCP Server**  | Agent ↔ memory interface — exposes find/aggregate as MCP tools via stdio subprocess                                                                                    |
| **FastMCP + Starlette** | MCP transport + REST API composition                                                                                                                                   |
| **MCP Protocol**        | Harness integration — supported by Cursor, Claude Code, Gemini CLI                                                                                                     |
| **Cloud Run**           | Stateless compute — HTTP request model, scale-to-zero, container flexibility                                                                                           |
| **SSE**                 | Reasoning Feed streaming — unidirectional, auto-reconnection via EventSource API                                                                                       |
| **Next.js**             | Reasoning Feed UI                                                                                                                                                      |
| **Python 3.14**         | Runtime — latest stable, ADK compatibility                                                                                                                             |

---

## Document Roadmap

| Document                                                        | Scope                                                                                                                                                                                                |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [02 — Data Model](./02-data-model.md)                           | MongoDB schema: memory_nodes (operational knowledge graph with embeddings), agent_events, sessions, api_tokens, tenants; index strategies (vector, text, compound); tenant isolation                 |
| [03 — ADK Agent Design](./03-adk-agent-design.md)               | Agent topology: LlmAgent orchestrator, subagent definitions (semantic_retriever, graph_explorer, memory_writer), AgentTool delegation, decision checkpoint emission, orchestrator instruction design |
| [04 — MCP Server Design](./04-mcp-server-design.md)             | Transport layer: single `canon` tool definition, FastMCP + Starlette composition, DI service wiring, RESTful API endpoints, SSE broadcast                                                            |
| [05 — Retrieval and Reasoning](./05-retrieval-and-reasoning.md) | Query pipelines: hybrid search via $rankFusion, graph traversal via $graphLookup, organizational reasoning strategy, semantic graph evolution                                                        |
| [06 — Memory Creation & Evolution](./06-memory-lifecycle.md)    | Memory creation, synchronous embedding, relationship cascade, semantic graph evolution via supersession                                                                                              |
