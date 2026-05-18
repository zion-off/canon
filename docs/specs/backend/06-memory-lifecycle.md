# 06 — Memory Creation & Evolution

How organizational memory grows and evolves in Canon's operational knowledge
graph. Memory doesn't have a lifecycle — it grows through conversation and
evolves through supersession. The reasoning layer interprets relevance
semantically, not through physical deletion.

---

## 1. Design Philosophy

Canon's memory is a living substrate. It grows through conversation. It evolves
through supersession. It never expires or gets deleted. Organizational memory
persists.

**Core principles:**

- **Memory is permanent.** Once canonized, a memory node is never physically
  deleted. The graph only grows.
- **Relevance is reasoned, not enforced.** The orchestrator interprets which
  memories are current vs. historical based on status, supersession chains,
  recency, and graph context.
- **Evolution is semantic.** When organizational knowledge changes, new nodes
  supersede old ones. The old node remains as historical context. The graph
  captures _why_ things changed.
- **Trust the reasoning layer.** Canon's intelligence is in its ability to weigh
  relevance across a rich, growing graph — not in mechanical cleanup rules or
  expiration timers.

---

## 2. Memory Creation Flow

Memory creation is conversational. The orchestrator decides what's worth
remembering based on the conversation — there is no write gate, no confirmation
parameter, no separate approval step.

### Trigger

Natural conversation. The orchestrator observes something worth persisting and
acts.

### Execution

1. Orchestrator determines an observation should become organizational memory
2. Orchestrator calls **memory_writer** subagent — structures the raw
   observation into a proper memory_node document:
   - Writes `name`, `description`, `content`
   - Sets appropriate `status`
   - Resolves `relatedEntityIds` from prior query results (max 100)
   - Sets `tags` and relevant `metadata`
   - Sets `supersedes` if this node replaces an existing decision/convention
3. Memory writer calls **`canonize_node`** FunctionTool with the structured
   document
4. `canonize_node` executes the write (see §2a below)
5. Events emitted to `agent_events` for reasoning visibility

### 2a. canonize_node Internals

`canonize_node` is the single write path for all memory creation. It validates,
embeds, persists, and maintains graph integrity in one synchronous operation.

```
canonize_node(document, rationale, related_existing_ids)
  │
  ├─ 1. Validate document against schema
  ├─ 2. Build embeddingText from document fields
  ├─ 3. Generate embedding vector synchronously (Gemini text-embedding-004)
  ├─ 4. Insert document into memory_nodes (with embedding)
  ├─ 5. Update relatedEntityIds on related nodes (bidirectional push)
  ├─ 6. If superseding: set supersededBy on predecessor, transition status → deprecated
  └─ 7. Return result to orchestrator
```

Events (`tool_call_started`, `tool_call_completed`) are emitted by the
`ReasoningFeedPlugin` (Doc 03 §8) which intercepts all tool calls — including
`canonize_node` — and broadcasts them to `agent_events`.

---

## 3. Synchronous Embedding

Embedding is generated inline during `canonize_node` execution. No queue, no
trigger, no worker, no retry infrastructure.

### embeddingText Construction

The `embeddingText` field is built from document fields using
`build_embedding_text` (see Doc 03 §4c). The function constructs a
retrieval-optimized representation: identity header (`name [status]`), followed
by description and content (capped at 1500 chars), closing with tags. Only
non-empty fields are included.

### Embedding Generation

### Embedding Generation

Embedding is generated synchronously via `generate_document_embedding` (see Doc
03 §4d), using `EMBEDDING_MODEL` with task type `RETRIEVAL_DOCUMENT`. The node
is immediately searchable after insertion — no async queue.

Simple, synchronous, within the write path. Every node has its embedding
immediately available for search after insertion.

---

## 4. Relationship Cascade (Atlas Trigger)

This is the **only** Atlas Trigger in Canon. It serves as an idempotent safety
net for bidirectional consistency. The primary write path (`canonize_node`)
performs edge and supersession updates inline during persistence. The trigger
ensures consistency for any direct database modifications (admin edits,
migrations) that bypass `canonize_node`.

### Behavior

When a node is inserted or updated, the trigger syncs reverse edges on affected
targets. All operations use `$addToSet` or `$set` — idempotent when
`canonize_node` has already performed the update.

```javascript
exports = async function (changeEvent) {
  const { fullDocument, fullDocumentBeforeChange } = changeEvent;
  const db = context.services.get("mongodb-atlas").db("canon");
  const collection = db.collection("memory_nodes");
  const sourceId = fullDocument._id;
  const RELATIONSHIP_CAP = 100;

  // --- Bidirectional relatedEntityIds sync ---
  const prevIds = fullDocumentBeforeChange?.relatedEntityIds || [];
  const currIds = fullDocument.relatedEntityIds || [];
  const added = currIds.filter((id) => !prevIds.includes(id));
  const removed = prevIds.filter((id) => !currIds.includes(id));

  for (const targetId of added) {
    await collection.updateOne(
      {
        _id: targetId,
        relatedEntityIds: { $ne: sourceId },
        $expr: { $lt: [{ $size: "$relatedEntityIds" }, RELATIONSHIP_CAP] },
      },
      { $push: { relatedEntityIds: sourceId } },
    );
  }

  for (const targetId of removed) {
    await collection.updateOne(
      { _id: targetId },
      { $pull: { relatedEntityIds: sourceId } },
    );
  }

  // --- Supersession sync ---
  const prevSupersedes = fullDocumentBeforeChange?.supersedes || null;
  const currSupersedes = fullDocument.supersedes || null;

  if (currSupersedes && currSupersedes !== prevSupersedes) {
    await collection.updateOne(
      { _id: currSupersedes },
      { $set: { supersededBy: sourceId, status: "deprecated" } },
    );
  }
};
```

### Eventual Consistency

The trigger runs asynchronously. One-directional edges may exist briefly between
trigger invocations. The system tolerates this — the orchestrator treats
relationships as hints, not invariants.

### Atlas Trigger Definition

```json
{
  "name": "sync_relationships",
  "type": "DATABASE",
  "config": {
    "service_name": "mongodb-atlas",
    "database": "canon",
    "collection": "memory_nodes",
    "operation_types": ["INSERT", "UPDATE"],
    "match": {
      "$or": [
        {
          "updateDescription.updatedFields.relatedEntityIds": {
            "$exists": true
          }
        },
        { "updateDescription.updatedFields.supersedes": { "$exists": true } },
        { "operationType": "insert" }
      ]
    },
    "full_document": true,
    "full_document_before_change": true
  },
  "function_name": "syncBidirectionalEdges"
}
```

---

## 5. Semantic Graph Evolution

Memory doesn't expire — it evolves via supersession. When organizational
understanding changes, new nodes supersede their predecessors. This creates
evolution chains that preserve history while surfacing current state.

### Supersession Model

```
supersedes:    ObjectId | null   — points to the node this one replaces (authored by agent)
supersededBy:  ObjectId | null   — points to the node that replaced this one (derived, never authored)
```

`supersedes` is the single source of truth. Only the new node's author sets it.
`supersededBy` is always a derived consequence — written on the predecessor by
`canonize_node` (primary) and the Atlas Trigger (safety net). No code path
should set `supersededBy` independently. This prevents graph drift where two
nodes disagree about their evolutionary relationship.

When a node is superseded:

- Its `status` transitions to `deprecated`
- Its `supersededBy` is set to the new node's `_id`
- The new node's `supersedes` points back to the predecessor
- Both nodes remain in the graph — fully searchable, fully traversable

### Supersession Chains Model Organizational Evolution

```
decision_012: "All inter-service comms use gRPC"
  status: "deprecated"
  supersededBy: decision_047

decision_047: "gRPC for inter-service; WebSocket allowed for client-facing real-time"
  status: "active"
  supersedes: decision_012
```

The reasoning layer interprets whether superseded knowledge is still relevant in
context. When the orchestrator finds decision*047, it can traverse `supersedes`
to understand \_what changed and why*. The full evolution chain is always
present.

---

## 6. Relevance Without Deletion

Canon **never** physically deletes organizational memory. The orchestrator
reasons about relevance using semantic signals — not expiration timers or
cleanup jobs.

### Relevance Signals

1. **Status.** `active` nodes represent current organizational state.
   `deprecated`, `resolved`, and `completed` represent history. The orchestrator
   weighs these appropriately.

2. **Recency.** `updatedAt` provides temporal signal. The orchestrator
   prioritizes recent nodes when the query implies currency.

3. **Supersession chains.** Following `supersededBy` finds the current version.
   Following `supersedes` provides lineage and context for _why_ things changed.

4. **Graph position.** Nodes with many relationships are structurally important.
   `$graphLookup` traversal identifies clusters of related knowledge.

5. **Semantic distance.** Vector search naturally surfaces the most conceptually
   relevant nodes. Stale or tangential memories score lower and fall below
   retrieval thresholds.

### Why Full History Matters

"Why did we decide X?" requires the full evolution chain to be present. Old
memories provide historical context even when superseded. The orchestrator
synthesizes current state while noting historical evolution — nothing was
deleted, the intelligence layer determined what mattered.

---

## 7. Demo Scenario

Memory growing through natural conversation, with supersession in practice:

1. Engineer: "I'm adding WebSocket support to notifications"
2. Canon queries memory → finds decision_012: "All inter-service comms use gRPC"
3. Canon surfaces the conflict: "Active decision requires gRPC for inter-service
   communication. WebSocket may conflict."
4. Engineer: "This is client-facing real-time, not inter-service. The gRPC
   decision still applies to inter-service calls but this refines the scope."
5. Orchestrator decides this is worth remembering → calls memory_writer →
   structures the refined decision
6. `canonize_node` persists → new decision node created with `supersedes` →
   decision_012
7. decision_012 transitions to `deprecated` with `supersededBy` pointing to the
   new node
8. Reasoning Feed shows: "Wrote: decision → gRPC for inter-service; WebSocket
   for client-facing real-time (supersedes decision_012)"
9. Future queries retrieve the **active** refined decision. If deeper context is
   needed, the orchestrator traverses the supersession chain to explain _why_
   the policy evolved.

---

## Summary

| Concern                | Mechanism                                                                               |
| ---------------------- | --------------------------------------------------------------------------------------- |
| Memory creation        | Conversational — orchestrator decides, memory_writer structures, canonize_node persists |
| Embedding              | Synchronous in canonize_node (Gemini text-embedding-004)                                |
| Relationship integrity | Atlas Trigger → bidirectional edge sync                                                 |
| Evolution              | supersedes/supersededBy chains                                                          |
| Relevance              | Semantic reasoning by orchestrator (not physical deletion)                              |
| Visibility             | agent_events + Reasoning Feed                                                           |
