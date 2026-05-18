# 02 — Data Model

MongoDB schema for Canon's semantic memory graph.

Canon's data layer is a memory substrate, not a typed ontology. Meaning lives in
text, embeddings, graph edges, and semantic retrieval — not in rigid schemas or
lifecycle machinery. The reasoning layer interprets structure; the storage layer
holds it faithfully.

---

## 1. Database & Collections

A single `canon` database within one Atlas cluster. All collections coexist in
the same namespace.

| Collection     | Purpose                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `memory_nodes` | The organizational memory graph. Polymorphic. Single collection enables `$graphLookup` traversal and cross-type hybrid search. |
| `sessions`     | Workflow session groups. Tenant + user scoped.                                                                                 |
| `agent_events` | Agent reasoning traces per invocation. Used for Reasoning Feed replay.                                                         |
| `tenants`      | Tenant configuration and metadata.                                                                                             |
| `api_tokens`   | Static tokens for harness authentication. Lookup: `api_tokens.token` → `tenantId` → `tenants`.                                 |
| `users`        | User accounts. Email/password credentials, tenant membership.                                                                  |
| `invites`      | Invite codes for joining a tenant. Time-limited, usage-capped.                                                                 |

**Why one `memory_nodes` collection?** `$graphLookup` requires a single `from`
collection for recursive traversal. Hybrid search queries span all node types —
"what do we know about payment service" returns decisions, incidents,
conventions, and whatever else the graph holds. A single polymorphic collection
makes this possible without unions or cross-collection joins.

**Why no separate embedding queue?** Embedding generation happens synchronously
during writes. The `canonize_node` pipeline constructs `embeddingText`,
generates the embedding vector, and persists both in a single write operation.
No background workers, no eventual consistency for embeddings.

---

## 2. Memory Node Schema

### Core Fields

```json
{
  "_id": "ObjectId",
  "tenantId": "ObjectId",
  "name": "string",
  "description": "string",
  "content": "string",
  "status": "string",
  "relatedEntityIds": ["ObjectId"],
  "supersedes": "ObjectId | null",
  "supersededBy": "ObjectId | null",
  "tags": ["string"],
  "embedding": [0.1, -0.02, ...],
  "embeddingText": "string",
  "metadata": {},
  "createdAt": "ISODate",
  "updatedAt": "ISODate"
}
```

| Field              | Description                                                                                                                                                                                                          |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_id`              | Document identifier.                                                                                                                                                                                                 |
| `tenantId`         | Tenant boundary. Every query includes this.                                                                                                                                                                          |
| `name`             | Human-readable node identity.                                                                                                                                                                                        |
| `description`      | Brief summary — what this node represents.                                                                                                                                                                           |
| `content`          | Full text body. ADR content, incident timelines, convention rules, meeting notes — whatever the memory holds.                                                                                                        |
| `status`           | Freeform semantic signal. Common values: `"active"`, `"deprecated"`, `"in_progress"`, `"resolved"`, `"completed"`. Not a closed enum — the reasoning layer interprets meaning.                                       |
| `relatedEntityIds` | Outgoing graph edges. The primary traversal mechanism for `$graphLookup`.                                                                                                                                            |
| `supersedes`       | ID of the node this node replaces, or `null`. The **authoritative** direction of supersession — set by the memory_writer when creating a replacement node.                                                           |
| `supersededBy`     | ID of the node that has replaced this one, or `null`. **Derived, never authored directly.** Set automatically by `canonize_node` (primary) and the Atlas Trigger (safety net) when a new node declares `supersedes`. |
| `tags`             | Lightweight semantic labels. Freeform strings. Used for filtering during retrieval, not for driving infrastructure behavior.                                                                                         |
| `embedding`        | 768-dimension vector (Gemini text-embedding). Generated synchronously at write time.                                                                                                                                 |
| `embeddingText`    | Retrieval-optimized text representation. Constructed by `canonize_node` at write time — a semantic compression of name, description, content, and tags tuned for embedding quality.                                  |
| `metadata`         | Freeform object. No enforced schema. The agent writes whatever contextual details are relevant — dates, URLs, numbers, references. The reasoning layer decides what matters at query time.                           |
| `createdAt`        | Document insertion time. Immutable.                                                                                                                                                                                  |
| `updatedAt`        | Last modification time. Updated on every write.                                                                                                                                                                      |

### Design Principles

**No entityType as infrastructure driver.** Tags provide semantic labeling
(e.g., `["decision", "architecture"]` or `["incident", "payments"]`), but
nothing in the infrastructure layer — indexes, triggers, validation — branches
on node type. The reasoning layer interprets what a node _is_ from its content
and graph position.

**No rigid metadata schemas.** A node representing a service might carry
`{"repo": "acme/orders", "language": "go"}` in metadata. A node representing an
incident might carry `{"postmortemUrl": "..."}`. These are contextual details
the agent deemed worth persisting, not a typed contract the system enforces.

**No temporal lifecycle management.** Nodes are not auto-deleted, expired, or
validity-windowed. Organizational memory accumulates. When knowledge evolves,
new nodes supersede old ones — the graph records the evolution rather than
erasing history.

**Supersession as first-class evolution.** When a decision is revised, the new
node carries `supersedes: oldNodeId` and the old node gains
`supersededBy: newNodeId`. This is how organizational knowledge moves forward
without losing context. The reasoning layer can follow supersession chains to
understand how and why things changed. Each node supersedes at most one other
node — if a node represents a synthesis of multiple prior nodes, the graph edges
in `relatedEntityIds` capture the broader context.

**`supersedes` is the source of truth.** Only `supersedes` is authored by the
agent. `supersededBy` is always derived — written by `canonize_node` on the
predecessor when a new node declares `supersedes`, and echoed by the Atlas
Trigger as a safety net. No code path should set `supersededBy` independently.
This single-direction authoring prevents graph drift where two nodes could
disagree about their relationship.

### Example Documents

#### A decision

```json
{
  "_id": ObjectId("665a1b2c3d4e5f6a7b8c9d01"),
  "tenantId": ObjectId("665a0000000000000000000a"),
  "name": "Use event sourcing for order service",
  "description": "ADR-042: Adopt event sourcing pattern for order lifecycle management",
  "content": "## Context\nThe order service handles complex state transitions...\n## Decision\nWe will use event sourcing with Kafka as the event store...\n## Consequences\n- Services must implement idempotent consumers\n- Need to maintain projection rebuilding capability",
  "status": "active",
  "relatedEntityIds": [
    ObjectId("665a1b2c3d4e5f6a7b8c9d10"),
    ObjectId("665a1b2c3d4e5f6a7b8c9d11")
  ],
  "supersedes": null,
  "supersededBy": null,
  "tags": ["decision", "architecture", "event-sourcing", "orders"],
  "embedding": [0.012, -0.034, 0.056, "...768 dims..."],
  "embeddingText": "Use event sourcing for order service [active]\nADR-042: Adopt event sourcing pattern for order lifecycle management\nWe will use event sourcing with Kafka as the event store. Services must implement idempotent consumers.\nTags: decision, architecture, event-sourcing, orders",
  "metadata": {
    "adrNumber": 42
  },
  "createdAt": ISODate("2024-09-15T10:00:00Z"),
  "updatedAt": ISODate("2024-09-15T10:00:00Z")
}
```

#### An incident

```json
{
  "_id": ObjectId("665a1b2c3d4e5f6a7b8c9d03"),
  "tenantId": ObjectId("665a0000000000000000000a"),
  "name": "INC-2025-017: Order service cascade failure",
  "description": "Payment timeout caused order-service retry storm, overwhelming inventory-service",
  "content": "## Timeline\n- 14:02 Payment gateway latency spike\n- 14:05 order-service retries exhaust connection pool\n- 14:08 inventory-service OOM killed\n- 14:15 Circuit breaker engaged\n- 14:22 Manual restart of inventory pods\n## Root Cause\nMissing exponential backoff on payment retries",
  "status": "resolved",
  "relatedEntityIds": [
    ObjectId("665a1b2c3d4e5f6a7b8c9d10"),
    ObjectId("665a1b2c3d4e5f6a7b8c9d11"),
    ObjectId("665a1b2c3d4e5f6a7b8c9d12")
  ],
  "supersedes": null,
  "supersededBy": null,
  "tags": ["incident", "outage", "cascade-failure", "retry-storm"],
  "embedding": [0.033, -0.015, 0.022, "...768 dims..."],
  "embeddingText": "INC-2025-017: Order service cascade failure [resolved]\nPayment timeout caused order-service retry storm, overwhelming inventory-service\nRoot cause: Missing exponential backoff on payment retries\nTags: incident, outage, cascade-failure, retry-storm",
  "metadata": {
    "postmortemUrl": "https://wiki.internal/postmortems/INC-2025-017",
    "durationMinutes": 20
  },
  "createdAt": ISODate("2025-01-08T14:02:00Z"),
  "updatedAt": ISODate("2025-01-09T11:00:00Z")
}
```

#### A superseded convention

```json
{
  "_id": ObjectId("665a1b2c3d4e5f6a7b8c9d50"),
  "tenantId": ObjectId("665a0000000000000000000a"),
  "name": "Use REST for inter-service communication",
  "description": "ADR-019: All service-to-service calls use REST/HTTP",
  "content": "## Context\nWe need a standard for inter-service communication...\n## Decision\nAll internal services communicate via REST APIs over HTTP/2.",
  "status": "deprecated",
  "relatedEntityIds": [
    ObjectId("665a1b2c3d4e5f6a7b8c9d10"),
    ObjectId("665a1b2c3d4e5f6a7b8c9d51")
  ],
  "supersedes": null,
  "supersededBy": ObjectId("665a1b2c3d4e5f6a7b8c9d51"),
  "tags": ["decision", "architecture", "communication"],
  "embedding": [0.018, -0.042, 0.011, "...768 dims..."],
  "embeddingText": "Use REST for inter-service communication [deprecated]\nADR-019: All service-to-service calls use REST/HTTP\nSuperseded by gRPC migration decision.\nTags: decision, architecture, communication",
  "metadata": {
    "adrNumber": 19
  },
  "createdAt": ISODate("2022-06-01T00:00:00Z"),
  "updatedAt": ISODate("2025-03-10T14:00:00Z")
}
```

---

## 3. Supporting Collections

### `sessions`

Groups related Canon invocations into a workflow session. Provides lightweight
semantic continuity across stateless runs.

```json
{
  "_id": "ObjectId",
  "tenantId": "ObjectId",
  "userId": "string",
  "sessionId": "string",
  "status": "string",
  "title": "string",
  "summary": "string | null",
  "runCount": "integer",
  "createdAt": "ISODate",
  "updatedAt": "ISODate",
  "lastRunAt": "ISODate"
}
```

**Session behavior:** Created on first `canon` invocation without an existing
`session_id`. Reused when `session_id` is passed. `runCount` increments each
invocation. `title` is auto-generated from the first request (~100 characters).

**`summary`:** A rolling semantic summary of the session's evolving context.
Generated post-run by a standalone `FAST_MODEL` call (a compression task outside
the ADK agent's execution — see Doc 04 §5 `_generate_session_summary`). Injected
into the orchestrator's context at the start of subsequent runs within the same
session, giving the agent continuity without persistent in-memory state.
Typically 2–3 sentences — enough to orient the agent on what was previously
discussed, decided, and written. Starts `null` on first run.

### `agent_events`

Agent reasoning traces per invocation. Used for Reasoning Feed replay.

```json
{
  "_id": "ObjectId",
  "tenantId": "ObjectId",
  "userId": "string",
  "sessionId": "string",
  "runId": "string",
  "sequence": "integer",
  "type": "string",
  "author": "string | null",
  "content": "string | null",
  "timestamp": "ISODate",
  "isFinal": "boolean"
}
```

Event types: `"reasoning_checkpoint"`, `"tool_call_started"`,
`"tool_call_completed"`, `"subagent_invoked"`, `"run_started"`,
`"run_completed"`.

### `tenants`

```json
{
  "_id": "ObjectId",
  "name": "string",
  "slug": "string",
  "embeddingModel": "string",
  "createdAt": "ISODate",
  "settings": {
    "maxGraphDepth": "integer"
  }
}
```

### `api_tokens`

Static tokens for harness authentication. Lookup: `token` → `tenantId` →
`tenants`.

```json
{
  "_id": "ObjectId",
  "tenantId": "ObjectId",
  "userId": "string | null",
  "token": "string",
  "label": "string",
  "createdAt": "ISODate",
  "lastUsedAt": "ISODate | null"
}
```

### `users`

User accounts for frontend authentication. Each user belongs to at most one
tenant.

```json
{
  "_id": "ObjectId",
  "email": "string",
  "name": "string",
  "passwordHash": "string",
  "tenantId": "ObjectId | null",
  "role": "owner | member | null",
  "createdAt": "ISODate",
  "updatedAt": "ISODate"
}
```

### `invites`

Invite codes for joining a tenant. Owner-generated, time-limited, usage-capped.

```json
{
  "_id": "ObjectId",
  "tenantId": "ObjectId",
  "code": "string",
  "createdBy": "ObjectId",
  "usesRemaining": "number",
  "expiresAt": "ISODate",
  "createdAt": "ISODate"
}
```

---

## 4. Graph Model

### Edges as ID Arrays

Relationships are stored as `relatedEntityIds` — an array of ObjectIds on each
document. `$graphLookup` requires `connectFromField` to reference a field on the
source document; this is the only viable shape for recursive traversal within a
single collection.

**Array size cap:** `relatedEntityIds` is limited to 100 entries per document
via schema validation. Prevents unbounded growth toward MongoDB's 16MB document
limit.

```javascript
db.runCommand({
  collMod: "memory_nodes",
  validator: {
    $jsonSchema: {
      properties: {
        relatedEntityIds: { bsonType: "array", maxItems: 100 },
      },
    },
  },
  validationLevel: "moderate",
});
```

### Bidirectional Edges

When node A relates to node B, both documents carry each other's ID in
`relatedEntityIds`. Maintained via Atlas Trigger (see Section 7).

**Eventual consistency:** The bidirectional sync trigger is asynchronous. The
system tolerates transient one-directional edges — `relatedEntityIds` are
traversal hints, not invariants. A node unreachable from one direction will
still surface via the other direction or via hybrid search.

Edges live on documents (not in a separate collection) because `$graphLookup`
requires a single `from` collection and resolves edges via a field on each
document — enabling recursive traversal in a single aggregation stage.

### Supersession Edges

`supersedes` and `supersededBy` are singular references — each node supersedes
at most one predecessor and is superseded by at most one successor. This models
a linear chain of knowledge evolution rather than a branching tree.

When the agent writes a supersession:

1. New node gets `supersedes: oldNodeId`
2. Old node gets `supersededBy: newNodeId` (via trigger)
3. Both nodes also appear in each other's `relatedEntityIds` (they are related)
4. The old node's `status` is typically set to `"deprecated"` by the agent

The reasoning layer follows supersession chains to understand knowledge
evolution: "This convention was replaced by X, which was later refined into Y."

### Graph Traversal

```javascript
// Traverse from a node to all transitively related nodes (depth 2)
db.memory_nodes.aggregate([
  { $match: { _id: nodeId, tenantId: tenantId } },
  {
    $graphLookup: {
      from: "memory_nodes",
      startWith: "$relatedEntityIds",
      connectFromField: "relatedEntityIds",
      connectToField: "_id",
      as: "graph",
      maxDepth: 2,
      depthField: "hops",
      restrictSearchWithMatch: { tenantId: tenantId },
    },
  },
]);
```

---

## 5. Indexes

### Atlas Vector Search Index

```javascript
{
  "name": "vector_search_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 768,
        "similarity": "cosine"
      },
      { "type": "filter", "path": "tenantId" },
      { "type": "filter", "path": "status" },
      { "type": "filter", "path": "tags" }
    ]
  }
}
```

### Atlas Search Index

```javascript
{
  "name": "text_search_index",
  "type": "search",
  "definition": {
    "mappings": {
      "dynamic": false,
      "fields": {
        "name": { "type": "string", "analyzer": "lucene.standard" },
        "description": { "type": "string", "analyzer": "lucene.standard" },
        "content": { "type": "string", "analyzer": "lucene.standard" },
        "tags": { "type": "token" },
        "tenantId": { "type": "objectId" },
        "status": { "type": "token" }
      }
    }
  }
}
```

### Standard Indexes

```javascript
// Tenant + status: primary query filter
db.memory_nodes.createIndex({ tenantId: 1, status: 1 });

// Relationship traversal: find all nodes that reference a given ID
db.memory_nodes.createIndex({ tenantId: 1, relatedEntityIds: 1 });

// Supersession traversal
db.memory_nodes.createIndex({ tenantId: 1, supersedes: 1 });
db.memory_nodes.createIndex({ tenantId: 1, supersededBy: 1 });

// Unique node names within a tenant
db.memory_nodes.createIndex({ tenantId: 1, name: 1 }, { unique: true });

// Tags filtering
db.memory_nodes.createIndex({ tenantId: 1, tags: 1 });

// api_tokens
db.api_tokens.createIndex({ token: 1 }, { unique: true });
db.api_tokens.createIndex({ tenantId: 1 });

// users
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ tenantId: 1 });

// invites
db.invites.createIndex({ code: 1 }, { unique: true });
db.invites.createIndex({ tenantId: 1, expiresAt: 1 });
db.invites.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 }); // TTL cleanup

// sessions
db.sessions.createIndex({ tenantId: 1, userId: 1, updatedAt: -1 });
db.sessions.createIndex({ sessionId: 1 }, { unique: true });

// agent_events
db.agent_events.createIndex({ tenantId: 1, sessionId: 1, sequence: 1 });
db.agent_events.createIndex({ tenantId: 1, userId: 1, createdAt: -1 });
```

---

## 6. Tenant Isolation

Every document carries `tenantId`. Every query includes it. Every index leads
with it.

```python
# Application-level: all queries are tenant-scoped
def tenant_query(query: dict, tenant_id: ObjectId) -> dict:
    return {**query, "tenantId": tenant_id}

# $graphLookup respects tenant boundary
{"$graphLookup": {
    "from": "memory_nodes",
    "startWith": "$relatedEntityIds",
    "connectFromField": "relatedEntityIds",
    "connectToField": "_id",
    "as": "graph",
    "maxDepth": 2,
    "restrictSearchWithMatch": {"tenantId": tenant_id}
}}
```

Vector search and text search both include `tenantId` as a filter field,
ensuring cross-tenant data is never surfaced in retrieval results.

---

## 7. Atlas Trigger — Relationship Cascade

A single trigger maintains bidirectional consistency as an idempotent safety
net. The primary write path (`canonize_node` in Doc 03 §4e) performs these
updates inline. The trigger ensures consistency for any direct database
modifications (admin edits, migrations, manual fixes) that bypass
`canonize_node`.

**On insert/update of `memory_nodes`:**

1. **`relatedEntityIds` sync:** Compute added/removed IDs relative to the
   previous state.
   - For added IDs: append current node's `_id` to the target's
     `relatedEntityIds`
   - For removed IDs: pull current node's `_id` from the target's
     `relatedEntityIds`

2. **`supersedes`/`supersededBy` sync:** When `supersedes` is set on a node:
   - Set the target node's `supersededBy` to the current node's `_id`
   - Set the target node's `status` to `"deprecated"`

All operations are idempotent (`$addToSet`, `$set`) — running both
`canonize_node` and the trigger produces the same result as either alone.

---

## 8. Hybrid Search Pipeline (Reference)

The retrieval pipeline combines vector and text search via `$rankFusion`, then
optionally expands graph context. In practice, graph expansion is a separate
sequential step — the agent inspects hybrid search results first and decides
whether expansion adds value (see Doc 05). This single-pipeline variant
documents the underlying MongoDB capability.

```javascript
db.memory_nodes.aggregate([
  {
    $rankFusion: {
      input: {
        pipelines: {
          vectorSearch: [
            {
              $vectorSearch: {
                index: "vector_search_index",
                path: "embedding",
                queryVector: queryEmbedding,
                numCandidates: 100,
                limit: 20,
                filter: { tenantId: tenantId },
              },
            },
          ],
          textSearch: [
            {
              $search: {
                index: "text_search_index",
                compound: {
                  must: [
                    {
                      text: {
                        query: searchText,
                        path: ["name", "description", "content"],
                      },
                    },
                  ],
                  filter: [{ equals: { path: "tenantId", value: tenantId } }],
                },
              },
            },
            { $limit: 20 },
          ],
        },
      },
      combination: { weights: { vectorSearch: 1.5, textSearch: 1.0 } },
    },
  },
  { $limit: 10 },
  { $project: { _id: 1, relatedEntityIds: 1, name: 1, tenantId: 1 } },
  {
    $graphLookup: {
      from: "memory_nodes",
      startWith: "$relatedEntityIds",
      connectFromField: "relatedEntityIds",
      connectToField: "_id",
      as: "context",
      maxDepth: 2,
      depthField: "hops",
      restrictSearchWithMatch: { tenantId: tenantId },
    },
  },
]);
```

**$rankFusion as first stage:** Each input pipeline is independent —
`$vectorSearch` satisfies its "must be first" constraint within its
sub-pipeline. The outer aggregation starts with `$rankFusion`, which executes
both and fuses via Reciprocal Rank Fusion.

**$project before $graphLookup:** Reduces document size before recursive
traversals. Full document hydration happens in a subsequent fetch after the
agent selects relevant nodes.
