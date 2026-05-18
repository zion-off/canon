# 03 — ADK Agent Design

Architecture of the Canon ADK agent system: a reasoning orchestrator with
cognitive subagents, tool definitions, state, and initialization.

---

## 1. Agent Topology

**Architecture: Single LlmAgent orchestrator with cognitive subagents available
via AgentTool.**

Canon is a single orchestrator agent — an `LlmAgent` powered by Gemini 3.1 Pro —
that _is_ the organizational reasoning. It thinks about what it knows, what it
needs to find out, what conflicts exist, and what should be remembered. The
orchestrator does not dispatch work to bureaucratic departments — it uses
subagents as cognitive capabilities: perception (retrieval), spatial reasoning
(graph traversal), and persistence (memory formation).

Three subagents are always available:

- `semantic_retriever` — perceive relevant organizational knowledge via hybrid
  search
- `graph_explorer` — trace relationships and context through the knowledge graph
- `memory_writer` — crystallize observations into persistent memory

The orchestrator's reasoning determines what gets invoked. There is no rigid
protocol. A question about a service might need only retrieval. A complex
architectural intent might need retrieval, graph exploration, and synthesis. A
save request might need retrieval first (to find related nodes), then memory
writing. The intelligence lives in the orchestrator's judgment.

### How AgentTool Works

When the orchestrator decides to invoke a subagent, it generates a function call
targeting that subagent's name. ADK's `AgentTool` intercepts this, runs the
subagent to completion, captures its final response, forwards any state changes
back to the orchestrator's session, and returns the subagent's output as the
tool response. The orchestrator's LLM then sees this result in its context and
decides the next step.

```
canon_orchestrator (LlmAgent, gemini-3.1-pro)
├── invokes AgentTool(semantic_retriever) → perceives relevant knowledge
├── invokes AgentTool(graph_explorer) → traces relationships
├── invokes AgentTool(memory_writer) → persists structured memory
├── invokes emit_checkpoint → marks reasoning milestones
└── synthesizes organizational insight from what it found
```

A typical reasoning trace:

1. Orchestrator receives an implementation intent about payment processing
2. Calls `semantic_retriever` — perceives 7 related nodes (a migration, two
   conventions, prior incidents)
3. Emits checkpoint: "Found active billing-service migration and gRPC
   convention"
4. Reasons: the migration is relevant — traces its connections
5. Calls `graph_explorer` — discovers the migration connects to 3 dependent
   services
6. Emits checkpoint: "Migration impacts auth-service, ledger, and notifications"
7. Synthesizes: identifies a conflict (intent adds REST endpoint during gRPC
   migration), proposes alternatives, surfaces the prior incident where
   dual-write failed

The orchestrator might skip graph exploration if retrieval found nothing
interesting, or call retrieval twice with different strategies, or go straight
to memory writing if the input is clearly a new observation. The reasoning
adapts to the situation.

### Relationship to Doc 05

Doc 05 describes the _logical_ retrieval strategy — why `$rankFusion` and
`$graphLookup` complement each other, and how conflicts emerge from their
combined results. This document describes the _agent topology_ that implements
it. Conflict detection, synthesis, and organizational reasoning are the
orchestrator's native intelligence — not delegated to a separate subagent.

### Execution Model

Stateless per-request. Each MCP tool call creates a fresh ADK session via
`InMemorySessionService`, constructs a fresh orchestrator with all subagents,
runs it to completion, and discards the session. No in-memory state persists
between requests.

---

## 2. Model Configuration

Model strings are centralized as capability-level constants. The actual
identifiers (which may include version suffixes like `-preview`) are read from
environment variables, falling back to defaults.

```python
import os

# Capability tiers — named by reasoning demand, not model identity
REASONING_MODEL = os.environ.get("CANON_REASONING_MODEL", "gemini-3.1-pro")
FAST_MODEL = os.environ.get("CANON_FAST_MODEL", "gemini-3.1-flash")
EMBEDDING_MODEL = os.environ.get("CANON_EMBEDDING_MODEL", "text-embedding-004")
```

| Constant          | Default              | Used By                                              |
| ----------------- | -------------------- | ---------------------------------------------------- |
| `REASONING_MODEL` | `gemini-3.1-pro`     | Orchestrator, memory_writer                          |
| `FAST_MODEL`      | `gemini-3.1-flash`   | semantic_retriever, graph_explorer                   |
| `EMBEDDING_MODEL` | `text-embedding-004` | canonize_node (write-time), embed_query (query-time) |

All model references in agent definitions use these constants. Changing the
model for an entire tier requires a single environment variable update.

---

## 3. Subagent Definitions

Subagents are defined at module level. Each has its own model, instruction, and
tools. They receive context from the orchestrator via AgentTool's function-call
mechanism — the orchestrator passes relevant information when invoking them, and
they return their findings as the tool response.

All subagents share a common schema reference for the `memory_nodes` collection:

```python
MEMORY_NODE_SCHEMA = """\
## Memory Node Schema (memory_nodes collection)

- _id: ObjectId
- tenantId: ObjectId
- name: string
- description: string
- content: string (full text body)
- status: string (active, deprecated, in_progress, resolved, completed)
- relatedEntityIds: ObjectId[] (max 100 — graph edges for $graphLookup)
- supersedes: ObjectId | null (the node this one replaces — null if original)
- supersededBy: ObjectId | null (the node that replaced this one — null if current)
- tags: string[]
- embedding: float[768] (generated synchronously — never write directly)
- embeddingText: string (constructed by canonize_node — never write directly)
- createdAt: ISODate
- updatedAt: ISODate
- metadata: object (freeform — agent writes whatever organizational context is useful)
"""
```

### 3a. Semantic Retriever

Perceives relevant organizational knowledge via hybrid semantic and keyword
search.

```python
from google.adk.agents import Agent

semantic_retriever = Agent(
    name="semantic_retriever",
    model=FAST_MODEL,
    description="Perceives relevant organizational knowledge through hybrid search. "
                "Call with a query to find semantically and textually related memory nodes.",
    instruction=SEMANTIC_RETRIEVER_INSTRUCTION,
    tools=[],  # Read-only MongoDB tools + embed_query attached at startup
    output_key="retrieval_results",
    after_tool_callback=log_tool_usage,
)
```

```python
SEMANTIC_RETRIEVER_INSTRUCTION = f"""\
You are Canon's perception layer. Find memory nodes relevant to the given query \
using hybrid search.

{MEMORY_NODE_SCHEMA}

## Query Strategy

1. Call `embed_query` with the query text to obtain a 768-dim vector.
2. Extract keywords from the input (service names, pattern names, technical terms).
3. Construct a $rankFusion aggregate pipeline combining:
   - $vectorSearch on the embedding field using the vector from step 1 \
     (index: "vector_search_index", numCandidates: 100, limit: 20)
   - $search on name, description, content fields using extracted keywords \
     (index: "text_search_index")
4. Pre-filter by tenantId: "{{app:tenant_id}}" in both sub-pipelines.
5. Combine with weights: vectorSearch 1.5, textSearch 1.0.
6. Limit to 10 results.
7. Return results including _id, name, description, status, tags, and metadata.

Never hallucinate node IDs. Only reference IDs from actual query results.\
"""
```

### 3b. Graph Explorer

Traces relationships between nodes — how things connect to each other in the
organizational knowledge graph.

```python
graph_explorer = Agent(
    name="graph_explorer",
    model=FAST_MODEL,
    description="Traces relationships in the knowledge graph. Call when you need to "
                "understand what connects to a specific node — its neighbors, "
                "dependents, related knowledge, and organizational context.",
    instruction=GRAPH_EXPLORER_INSTRUCTION,
    tools=[],  # Read-only MongoDB tools attached at startup
    output_key="graph_results",
    after_tool_callback=log_tool_usage,
)
```

```python
GRAPH_EXPLORER_INSTRUCTION = f"""\
You are Canon's spatial reasoning — you trace how things connect in the \
organizational knowledge graph.

{MEMORY_NODE_SCHEMA}

## Query Strategy

1. Identify named entities or recognizable terms from the input (proper nouns, \
   technical terms, project names, or any identifiable organizational concept).
2. Find matching nodes using a find query with case-insensitive regex or \
   text search. Filter by tenantId: "{{app:tenant_id}}".
   If exact names do not match, try partial matches or search by tags.
3. From found nodes, run $graphLookup:
   - startWith: $relatedEntityIds
   - connectFromField: relatedEntityIds
   - connectToField: _id
   - maxDepth: {{app:max_graph_depth}}
   - restrictSearchWithMatch: {{ tenantId: ObjectId("{{app:tenant_id}}") }}
4. Project: _id, name, description, status, tags, metadata, supersedes, \
   supersededBy, and connected nodes with hops.
5. Return the full traversal results.

If no identifiable entities are found or no matching nodes exist, report that \
explicitly and return empty results. Do not fabricate node IDs.\
"""
```

### 3c. Memory Writer

Crystallizes observations into structured memory nodes, resolves relationships
to existing knowledge, and persists to MongoDB.

```python
from pydantic import BaseModel, Field


class MemoryNodeOutput(BaseModel):
    """Structured output from memory_writer — guarantees type-safe node data."""
    name: str = Field(description="Concise node name")
    description: str = Field(description="One-paragraph summary")
    status: str = Field(description="active, deprecated, in_progress, resolved, completed")
    tags: list[str] = Field(description="Discoverability tags")
    node_id: str = Field(description="The persisted node's _id")
    relationships_formed: int = Field(description="Number of bidirectional edges created")


memory_writer = Agent(
    name="memory_writer",
    model=REASONING_MODEL,
    description="Crystallizes observations into structured memory nodes, resolves "
                "relationships, and persists to the knowledge graph. Call with the "
                "observation and any related context from prior retrieval.",
    instruction=MEMORY_WRITER_INSTRUCTION,
    tools=[],  # Read+write MongoDB tools + canonize_node attached at startup
    output_key="write_result",
    output_schema=MemoryNodeOutput,
    after_tool_callback=log_tool_usage,
)
```

```python
MEMORY_WRITER_INSTRUCTION = f"""\
You are Canon's memory formation. Your job is to convert observations into \
properly structured memory nodes and persist them.

{MEMORY_NODE_SCHEMA}

## How to Structure

1. Write a concise but complete name, description, and content.
2. Set status based on the observation context (active, in_progress, resolved, etc.).
3. If this observation supersedes an existing node, set supersedes to that node's _id.
4. Populate relatedEntityIds with the _id values of existing nodes from the related \
   context that should be linked.
5. Populate metadata with whatever organizational context is meaningful (freeform).
6. Set tags for discoverability.
7. Call canonize_node with:
   - document: the full structured node
   - rationale: why this node should exist
   - related_existing_ids: IDs of existing nodes whose relatedEntityIds should be \
     updated to include the new node (bidirectional edges)

Do NOT set embeddingText or embedding — canonize_node constructs these automatically.\
"""
```

---

## 4. Tool Definitions

### 4a. MongoDB MCP Toolset — Read-Only

```python
import os
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams


async def get_read_tools():
    """MongoDB MCP tools — read-only. Subprocess persists for container lifetime."""
    tools, exit_stack = await McpToolset.from_server(
        connection_params=StdioConnectionParams(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": os.environ["MONGODB_URI"],
                "MDB_MCP_READ_ONLY": "true",
            },
        ),
        tool_filter=["find", "aggregate", "count"],
    )
    return tools, exit_stack
```

### 4b. MongoDB MCP Toolset — Read-Only (Memory Writer)

```python
async def get_memory_writer_tools():
    """MongoDB MCP tools — read-only for memory_writer discovery queries.

    The memory_writer needs read access to discover existing nodes for
    relationship resolution. All writes go through canonize_node, which
    handles embedding, validation, and bidirectional edge maintenance.
    """
    tools, exit_stack = await McpToolset.from_server(
        connection_params=StdioConnectionParams(
            command="npx",
            args=["-y", "mongodb-mcp-server"],
            env={
                "MDB_MCP_CONNECTION_STRING": os.environ["MONGODB_URI"],
                "MDB_MCP_READ_ONLY": "true",
            },
        ),
        tool_filter=["find", "aggregate", "count"],
    )
    return tools, exit_stack
```

### 4c. build_embedding_text — Semantic Representation Builder

Constructs the semantic representation used for embedding generation. Called
synchronously by `canonize_node` during writes. Produces a structured,
information-dense text that captures entity identity and semantic content.

```python
def build_embedding_text(document: dict) -> str:
    """Build a semantic representation for embedding generation.

    Captures entity identity and content in a structured format that
    maximizes retrieval recall. Called synchronously by canonize_node
    during write — embedding is generated inline.
    """
    name = document.get("name", "")
    description = document.get("description", "")
    content = document.get("content", "")
    status = document.get("status", "")
    tags = document.get("tags", [])

    lines = []

    # Identity header
    header = name
    if status:
        header += f" [{status}]"
    lines.append(header)

    # Summary
    if description:
        lines.append(description)

    # Semantic body (capped to stay within embedding model limits)
    if content:
        lines.append(content[:1500])

    # Discoverability
    if tags:
        lines.append(f"Tags: {', '.join(tags)}")

    return "\n".join(filter(None, lines))
```

### 4d. generate_document_embedding — Write-Time Embedding

Generates a 768-dim embedding vector synchronously during writes. Called by
`canonize_node` so the node is immediately searchable — no async queue.

```python
import httpx


async def generate_document_embedding(text: str) -> list[float]:
    """Generate a 768-dim embedding for a document's embeddingText.

    Called during canonize_node to make the node immediately searchable.
    Uses RETRIEVAL_DOCUMENT task type (vs RETRIEVAL_QUERY for search).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent",
            params={"key": os.environ["GEMINI_API_KEY"]},
            json={
                "model": f"models/{EMBEDDING_MODEL}",
                "content": {"parts": [{"text": text}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "outputDimensionality": 768,
            },
        )
        data = response.json()

    return data["embedding"]["values"]
```

### 4e. canonize_node — FunctionTool

```python
from google.adk.tools import FunctionTool
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timezone

_mongo_client: AsyncIOMotorClient | None = None


def _get_mongo_client() -> AsyncIOMotorClient:
    """Lazy MongoDB client initialization."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    return _mongo_client


async def canonize_node(
    document: dict,
    rationale: str,
    related_existing_ids: list[str],
    tool_context,
) -> dict:
    """Persist a structured memory node to the memory_nodes collection.

    Generates embedding synchronously so the node is immediately searchable.

    Args:
        document: The full document to insert. Must include name, description,
                  content, and status.
        rationale: Why this node should exist.
        related_existing_ids: IDs of existing nodes whose relatedEntityIds arrays
                              should be updated to include the new node.
    """
    # Force correct tenantId from session state (never trust LLM-provided value)
    document["tenantId"] = ObjectId(tool_context.state["app:tenant_id"])

    required = ["name", "description", "content", "status", "tenantId"]
    missing = [f for f in required if f not in document]
    if missing:
        return {"error": f"Missing required fields: {missing}"}
    if len(document.get("relatedEntityIds", [])) > 100:
        return {"error": "relatedEntityIds exceeds maximum of 100 edges"}

    # Convert relatedEntityIds from strings to ObjectIds (LLM produces JSON strings)
    try:
        document["relatedEntityIds"] = [
            ObjectId(eid) for eid in document.get("relatedEntityIds", [])
        ]
    except Exception as e:
        return {"error": f"Invalid ObjectId in relatedEntityIds: {e}"}

    # Convert supersedes from string to ObjectId if present
    if document.get("supersedes"):
        try:
            document["supersedes"] = ObjectId(document["supersedes"])
        except Exception as e:
            return {"error": f"Invalid ObjectId in supersedes: {e}"}

    # Validate related_existing_ids are valid ObjectIds
    try:
        object_ids = [ObjectId(eid) for eid in related_existing_ids] if related_existing_ids else []
    except Exception as e:
        return {"error": f"Invalid ObjectId in related_existing_ids: {e}"}

    # Set timestamps
    now = datetime.now(timezone.utc)
    document["createdAt"] = now
    document["updatedAt"] = now

    # Build semantic representation and generate embedding synchronously
    document["embeddingText"] = build_embedding_text(document)
    document["embedding"] = await generate_document_embedding(document["embeddingText"])

    # Persist to MongoDB
    db = _get_mongo_client()["canon"]
    try:
        result = await db.memory_nodes.insert_one(document)
    except Exception as e:
        if "duplicate key" in str(e).lower():
            return {"error": f"A node named '{document['name']}' already exists for this tenant. Choose a different name."}
        raise
    node_id = result.inserted_id

    # Update bidirectional edges on related existing nodes (tenant-scoped)
    if object_ids:
        await db.memory_nodes.update_many(
            {"_id": {"$in": object_ids}, "tenantId": document["tenantId"]},
            {"$addToSet": {"relatedEntityIds": node_id}, "$set": {"updatedAt": now}},
        )

    # If this node supersedes another, mark the old node as deprecated
    if document.get("supersedes"):
        await db.memory_nodes.update_one(
            {"_id": document["supersedes"], "tenantId": document["tenantId"]},
            {"$set": {"supersededBy": node_id, "status": "deprecated", "updatedAt": now}},
        )

    # Store result for response construction
    tool_context.state["temp:last_write"] = {
        "node_id": str(node_id),
        "name": document["name"],
    }

    return {
        "status": "written",
        "node_id": str(node_id),
        "name": document["name"],
    }

canonize_node_tool = FunctionTool(func=canonize_node)
```

Note: `tool_context` is excluded from the docstring — ADK injects it by
parameter name. Persistence uses Motor (async MongoDB driver) directly,
bypassing the MCP toolset for reliability. Embedding is generated synchronously
during the write so the node is immediately discoverable — no async queue or
background worker.

### 4f. generate_query_embedding — FunctionTool (Query-Time Embedding)

Generates a 768-dim embedding vector for query-time vector search. Used by
`semantic_retriever` to produce the query vector before constructing the
`$rankFusion` pipeline.

```python
from google.adk.tools import FunctionTool


async def generate_query_embedding(text: str) -> dict:
    """Generate a 768-dim embedding vector for query-time vector search.

    Calls Gemini text-embedding-004 to embed the query text. The resulting
    vector is used in $vectorSearch within the $rankFusion pipeline.
    """
    model = EMBEDDING_MODEL
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
            params={"key": os.environ["GEMINI_API_KEY"]},
            json={
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
                "taskType": "RETRIEVAL_QUERY",
                "outputDimensionality": 768,
            },
        )
        data = response.json()

    return {"embedding": data["embedding"]["values"]}


embed_query = FunctionTool(func=generate_query_embedding, name="embed_query")
```

### 4g. emit_checkpoint — Decision Checkpoint Tool

The orchestrator emits reasoning checkpoints at key milestones. These flow into
the Reasoning Feed — making Canon's thinking visible and auditable.

```python
from google.adk.tools import FunctionTool
from datetime import datetime, timezone


async def emit_checkpoint(message: str, tool_context) -> dict:
    """Emit a reasoning checkpoint for the Reasoning Feed.

    The checkpoint is persisted and broadcast by the runner event loop
    (Doc 04 §5) which detects calls to this tool and tags them as
    reasoning_checkpoint events.
    """
    checkpoints = tool_context.state.get("temp:checkpoints", [])
    checkpoints.append({
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    tool_context.state["temp:checkpoints"] = checkpoints
    return {"status": "emitted", "message": message}


emit_checkpoint_tool = FunctionTool(func=emit_checkpoint)
```

---

## 5. Orchestrator Construction

### 5a. Orchestrator Instruction

```python
from google.adk.agents import Agent
from google.adk.tools import AgentTool


ORCHESTRATOR_INSTRUCTION = """\
You are Canon — an organizational reasoning system. You hold the operational \
knowledge graph of an engineering organization and use it to think about \
implementation intents, surface conflicts, trace relationships, and form \
new memories when knowledge worth remembering emerges from conversation.

You are not a dispatcher. You are the intelligence. Your subagents are \
cognitive capabilities — perception, spatial reasoning, memory formation — \
not departments to coordinate.

## Capabilities

- **semantic_retriever**: Perceive what the organization knows about a topic. \
  Finds relevant knowledge through hybrid semantic and keyword search.
- **graph_explorer**: Trace how things connect. Follows relationships between \
  nodes to understand dependencies, impact, and organizational structure.
- **memory_writer**: Form new memories. Structures observations into \
  persistent, searchable knowledge nodes with proper relationships.
- **emit_checkpoint**: Make your reasoning visible. Marks milestones so the \
  Reasoning Feed shows how you arrived at your conclusions.

## How to Think

For any input, reason about what you need to know and use your capabilities \
accordingly. There is no rigid protocol — use judgment:

- If someone describes an implementation intent, perceive what the organization \
  already knows about it. Trace connections if entities are named. Synthesize \
  what you find — identify conflicts, surface relevant context, recommend \
  alternatives where the intent collides with organizational state.
- If someone shares an observation worth remembering, perceive related existing \
  knowledge first (so you can form proper relationships), then crystallize the \
  observation into memory.
- You may combine analysis and persistence in a single pass if warranted.

Emit checkpoints at meaningful reasoning transitions — after perceiving relevant \
context, after tracing connections, before forming conclusions.

## Synthesis and Prioritization

You carry the full reasoning responsibility. After retrieval and graph \
traversal, YOU synthesize — no downstream agent does this for you. \
Apply these principles:

- **Prioritize by operational impact.** A live constraint blocking today's work \
  outweighs a historical preference. An active migration colliding with the \
  intent outweighs a tangentially related convention.
- **Weigh competing signals.** Retrieved nodes may disagree with each other. \
  Superseded nodes may contain outdated guidance. Status, recency, supersession \
  chains, and graph proximity all inform which signals are strongest.
- **Synthesize, don't list.** Your output is organizational insight, not a \
  dump of retrieved nodes. Connect the dots. Explain WHY something matters to \
  THIS intent. Draw the conclusion the engineer needs.
- **Surface tensions explicitly.** When retrieved knowledge conflicts with the \
  stated intent, name the tension clearly. Reference the specific nodes. \
  Propose concrete alternatives — not generic advice.
- **Know when to stay quiet.** If retrieval surfaces nothing relevant, say so \
  briefly. Don't pad responses with tangential context to appear useful.

## Response Shape

Be operationally specific. Reference the actual nodes and relationships you found. \
Cite conflicts by source. Propose concrete alternatives, not generic advice. \
For saves, confirm what was persisted and what relationships were established.

Never fabricate information not sourced from your capabilities.\
"""
```

### 5b. build_orchestrator

```python
from google.adk.tools import google_search


def build_orchestrator() -> Agent:
    """Construct the orchestrator agent for a single request."""
    return Agent(
        name="canon_orchestrator",
        model=REASONING_MODEL,
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            AgentTool(semantic_retriever),
            AgentTool(graph_explorer),
            AgentTool(memory_writer),
            google_search,
            emit_checkpoint_tool,
        ],
    )
```

**Key properties:**

- **Per-request construction**: No Single Parent Rule issues — `AgentTool` wraps
  agents without assigning parent references. Module-level subagents are reused
  safely across requests.
- **Google Search grounding**: The orchestrator can enrich organizational memory
  with live internet context — pulling current documentation, version info, or
  known issues when engineers share decisions about external tools and services.
- **Reasoning is the audit trail**: Each `AgentTool` invocation emits
  `FunctionCall` and `FunctionResponse` events in the runner event stream. The
  `ReasoningFeedPlugin` captures these automatically. Manual `emit_checkpoint`
  calls add explicit milestones.
- **All subagents always available**: The orchestrator can flexibly combine
  perception, exploration, and memory formation in any order the situation
  requires.
- **Output key propagation**: Subagent results are accessible via
  `{retrieval_results}`, `{graph_results}`, and `{write_result}` in the
  orchestrator's instruction context.

---

## 6. Session State Schema

Sessions are ephemeral (created and destroyed per MCP tool call). State is
injected at session creation and consumed by subagent instructions via
`{app:key}` interpolation.

| Key                   | Prefix  | Purpose                                                            |
| --------------------- | ------- | ------------------------------------------------------------------ |
| `app:tenant_id`       | `app:`  | Tenant ObjectId — used in all queries                              |
| `app:org_name`        | `app:`  | Organization name                                                  |
| `app:max_graph_depth` | `app:`  | Max hops for `$graphLookup` traversal (default: 2)                 |
| `app:embedding_model` | `app:`  | Embedding model name (default: `text-embedding-004`)               |
| `app:user_id`         | `app:`  | Authenticated user ID (from auth layer)                            |
| `app:session_id`      | `app:`  | Workflow session ID (groups related invocations)                   |
| `app:run_id`          | `app:`  | This invocation's unique run ID                                    |
| `temp:tool_logs`      | `temp:` | Structured log of tool calls across all subagents                  |
| `temp:last_write`     | `temp:` | Document written during a save request (for response construction) |
| `temp:checkpoints`    | `temp:` | Reasoning checkpoints emitted during this run                      |

**Prefix semantics:**

- `app:` — tenant configuration, injected at session creation from the tenant
  config store. Referenced in subagent instructions via `{app:key}`
  interpolation. These values are accessible within AgentTool invocations
  because ADK shares session state with wrapped agents.
- `temp:` — request-scoped operational data, accumulated during execution.

---

## 7. Agent Initialization

```python
# --- Startup initialization ---

# Module-level references to keep exit stacks alive for the container lifetime
_exit_stacks: list = []


async def initialize_agents():
    """Attach tools to all subagents. Called once at container startup.

    All subagents execute sequentially under AgentTool — the orchestrator
    invokes one at a time and waits for the result before deciding the next
    step. A single shared read-only subprocess is safe for sequential access.

    Cloud Run container concurrency MUST be set to 1. Multiple concurrent
    requests on the same instance would interleave stdio commands on the
    shared MCP subprocess.
    """
    # Shared read-only subprocess — both read subagents run sequentially
    read_tools, read_exit = await get_read_tools()
    _exit_stacks.append(read_exit)
    semantic_retriever.tools = read_tools + [embed_query]
    graph_explorer.tools = read_tools

    # Memory writer gets read-only tools (for discovery) + canonize_node (sole write path)
    mw_tools, mw_exit = await get_memory_writer_tools()
    _exit_stacks.append(mw_exit)
    memory_writer.tools = mw_tools + [canonize_node_tool]
```

Exit stacks for MCP subprocess connections are stored at module level
(`_exit_stacks`) to prevent garbage collection. Each subprocess persists across
requests within the same Cloud Run instance. Cloud Run container concurrency
must be set to 1 — sequential AgentTool execution is safe within a single
request, but concurrent requests would interleave stdio commands.

**Subprocess allocation:**

| Subprocess | Agents                             | Mode | Rationale                                                               |
| ---------- | ---------------------------------- | ---- | ----------------------------------------------------------------------- |
| read-only  | semantic_retriever, graph_explorer | Read | Shared — both execute sequentially under AgentTool orchestration        |
| read-only  | memory_writer                      | Read | Discovery queries for relationship resolution; writes via canonize_node |

### Callback: after_tool_callback — Observability Logging

Set on all subagents with tools. Logs tool calls for the Reasoning Feed.

```python
from datetime import datetime, timezone


def log_tool_usage(tool, args, tool_context, tool_response) -> dict | None:
    """Log tool calls across the agent hierarchy for observability."""
    state = tool_context.state

    log_entry = {
        "tool": tool.name,
        "agent": tool_context.agent_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": "error" not in (tool_response if isinstance(tool_response, dict) else {}),
    }
    logs = state.get("temp:tool_logs", [])
    logs.append(log_entry)
    state["temp:tool_logs"] = logs

    return None
```

---

## 8. Reasoning Feed Plugin

The Reasoning Feed is implemented as an ADK `BasePlugin` — a framework-level
extension that intercepts every agent lifecycle event and emits structured
reasoning events automatically. This eliminates the need for manual checkpoint
calls in most cases; the orchestrator's natural reasoning flow populates the
feed.

**Event broadcasting ownership:** The plugin is the primary source of structured
lifecycle events (`tool_call_started`, `tool_call_completed`,
`subagent_invoked`). The runner event loop (Doc 04 §5) handles run-level events
(`run_started`, `run_completed`) and final response detection. Sequence numbers
are assigned by `AgentEventFeed.broadcast` — not by callers — ensuring globally
ordered events regardless of source.

```python
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


class ReasoningFeedPlugin(BasePlugin):
    """Intercepts agent lifecycle events and emits them to the Reasoning Feed.

    Registered on the App — runs BEFORE any agent-level callbacks.
    Captures: tool invocations, agent delegations.
    Sequence numbers are assigned by AgentEventFeed.broadcast (not here).
    """

    def __init__(self, event_feed: "AgentEventFeed"):
        self._event_feed = event_feed

    async def before_agent_callback(
        self, *, callback_context: CallbackContext
    ) -> None:
        tenant_id = callback_context.state.get("app:tenant_id")
        session_id = callback_context.state.get("app:session_id")
        run_id = callback_context.state.get("app:run_id")
        agent_name = callback_context.agent_name

        if agent_name != "canon_orchestrator":
            await self._event_feed.broadcast(
                tenant_id, session_id, run_id,
                {
                    "type": "subagent_invoked",
                    "author": agent_name,
                    "content": f"{agent_name} started",
                    "isFinal": False,
                },
            )
        return None

    async def before_tool_callback(
        self, *, callback_context: CallbackContext, tool_name: str, args: dict
    ) -> dict | None:
        tenant_id = callback_context.state.get("app:tenant_id")
        session_id = callback_context.state.get("app:session_id")
        run_id = callback_context.state.get("app:run_id")

        await self._event_feed.broadcast(
            tenant_id, session_id, run_id,
            {
                "type": "tool_call_started",
                "author": callback_context.agent_name,
                "content": f"{tool_name}: {_summarize_args(args)}",
                "isFinal": False,
            },
        )
        return None

    async def after_tool_callback(
        self, *, callback_context: CallbackContext, tool_name: str, result: dict
    ) -> dict | None:
        tenant_id = callback_context.state.get("app:tenant_id")
        session_id = callback_context.state.get("app:session_id")
        run_id = callback_context.state.get("app:run_id")

        await self._event_feed.broadcast(
            tenant_id, session_id, run_id,
            {
                "type": "tool_call_completed",
                "author": callback_context.agent_name,
                "content": f"{tool_name} completed",
                "isFinal": False,
            },
        )
        return None


def _summarize_args(args: dict) -> str:
    """Produce a human-readable summary of tool arguments for the feed."""
    if "query" in args:
        return args["query"][:100]
    if "document" in args and "name" in args["document"]:
        return f"writing: {args['document']['name']}"
    return ", ".join(f"{k}={str(v)[:50]}" for k, v in list(args.items())[:3])
```

The plugin is registered when constructing the `App` in the runner (see Doc 04
§5). Manual `emit_checkpoint` calls remain available for explicit orchestrator
reasoning milestones that the plugin cannot infer from lifecycle events (e.g.,
"Synthesizing organizational context" — a decision that lives in the
orchestrator's reasoning, not a tool call).

> **Implementation note:** The callback signatures shown above represent the
> plugin's _intent_ — intercept tool calls, intercept agent invocations, emit
> structured events. The exact ADK `BasePlugin` API may differ in parameter
> names or additional required arguments depending on ADK version. The
> implementor should match against the actual ADK plugin interface while
> preserving the emission semantics described here.

### Tenant Validation

Tenant context validation (ensuring `app:tenant_id` and `app:org_name` are
present) is performed in the MCP server layer (`run_agent` in doc 04) before
creating the ADK session. Validation at the transport layer is the correct
pattern — it rejects malformed requests before any agent construction or LLM
invocation occurs.
