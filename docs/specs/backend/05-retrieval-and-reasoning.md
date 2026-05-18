# 05 — Retrieval and Reasoning

Canon retrieves from its organizational memory graph and reasons over what it
finds. Retrieval is perception — hybrid search and graph traversal surface the
relevant slice of organizational memory. Reasoning is organic intelligence — the
orchestrator interprets context, surfaces tensions, connects patterns, and
synthesizes understanding. This is not a mechanical detection pipeline with
categories. Trust the intelligence.

---

## 1. Retrieval Strategy Overview

Canon's retrieval is multi-step, orchestrated by the LLM within the
orchestrator's analysis phase:

1. **Intent embedding** — Convert the query intent to a 768-dim vector via
   Gemini text-embedding-004.
2. **Hybrid search** — `$rankFusion` combines vector similarity (semantic) with
   keyword matching (exact terms).
3. **Graph expansion** — `$graphLookup` traverses `relatedEntityIds` edges from
   top results.

The agent decides which steps are needed and in what order. A query like "what
conventions apply to the payments service?" triggers all three. A query like
"who owns billing-api?" may skip vector search and go straight to a filtered
find + graph traversal. A query that names a specific known decision might go
directly to graph expansion from that node.

Retrieval surfaces raw organizational context. The orchestrator then reasons
over it — that reasoning is where Canon's value lives.

---

## 2. Embedding Generation

| Aspect     | Detail                                                                                                     |
| ---------- | ---------------------------------------------------------------------------------------------------------- |
| Model      | Gemini text-embedding-004                                                                                  |
| Dimensions | 768                                                                                                        |
| Input text | `embeddingText` — retrieval-optimized semantic representation constructed by `canonize_node` at write time |
| Write-time | Synchronous — `canonize_node` generates the embedding inline before insert                                 |
| Query-time | Intent embedded on-the-fly before vector search                                                            |

### Synchronous Embedding During canonize_node

Embedding happens inline during the write path. When `canonize_node` persists a
memory node, it:

1. Constructs `embeddingText` from the structured document fields
2. Calls the Gemini embedding API with that text
3. Writes the resulting 768-dim vector into the `embedding` field
4. Inserts the complete document (with `embeddingText` and `embedding`
   populated)

No queue. No worker. No retry pipeline. No eventual consistency. A node is
retrievable via vector search immediately after write confirmation.

### embeddingText Construction

`embeddingText` is a retrieval-optimized semantic representation — not a naive
concatenation of raw fields. The representation leads with name and status
(identity header), followed by description (summary) and content (semantic body,
capped at 1500 chars), and closes with tags. This structure optimizes for
retrieval recall by preserving organizational identity and context that raw
field concatenation would flatten into noise.

### Query-Time Embedding

When the orchestrator prepares a hybrid search, it embeds the user's
natural-language intent using the same model. This produces a 768-dim vector in
the same embedding space as stored documents, enabling cosine similarity to
capture semantic equivalence between the query and organizational memory.

---

## 3. Hybrid Search Pipeline ($rankFusion)

The primary retrieval query the agent constructs via the MongoDB MCP `aggregate`
tool:

```javascript
db.memory_nodes.aggregate([
  { $rankFusion: {
      input: {
        pipelines: {
          vectorSearch: [
            { $vectorSearch: {
                index: "vector_search_index",
                path: "embedding",
                queryVector: <embedding>,
                numCandidates: 100,
                limit: 20,
                filter: { tenantId: <tenantId> }
            }}
          ],
          textSearch: [
            { $search: {
                index: "text_search_index",
                compound: {
                  must: [{ text: { query: <keywords>, path: ["name", "description", "content"] } }],
                  filter: [{ equals: { path: "tenantId", value: <tenantId> } }]
                }
            }},
            { $limit: 20 }
          ]
        }
      },
      combination: { weights: { vectorSearch: 1.5, textSearch: 1.0 } }
  }},
  { $limit: 10 }
])
```

### Retrieval Characteristics

The pipeline weights favor vector (1.5) over text (1.0) because implementation
intents are natural-language descriptions — semantic similarity captures "intent
equivalence" even when terminology differs (e.g., "retry logic" matches
"exponential backoff policy"). Text search serves as a precision anchor for
named entities and conventions.

The 5× over-retrieval ratio (`numCandidates: 100` for `limit: 20`) gives the ANN
index room to correct approximation errors with 768-dim cosine vectors.
Pre-filtering on `tenantId` in both sub-pipelines ensures multi-tenant isolation
at the index scan level, keeping latency predictable.

The LLM generates the `aggregate` tool call with the pipeline as argument. The
`<embedding>` placeholder is filled by calling the embedding API on the user's
intent text. The `<keywords>` are extracted by the LLM — typically service
names, pattern names, or technical terms.

### When Vector Helps vs Keyword

| Scenario                                                   | Primary modality                |
| ---------------------------------------------------------- | ------------------------------- |
| "What's our approach to error handling in async services?" | Vector — semantic concept       |
| "Find the ADR for billing-api migration"                   | Text — exact entity name        |
| "Are there conventions about retry backoff?"               | Both — concept + technical term |

The weights ensure that when both modalities fire, semantic relevance dominates,
but keyword precision still influences ranking.

---

## 4. Graph Expansion ($graphLookup)

After hybrid search returns the top results, the agent may run a second query to
expand the graph around those results:

```javascript
db.memory_nodes.aggregate([
  { $match: { _id: { $in: <result_ids> }, tenantId: <tenantId> } },
  { $graphLookup: {
      from: "memory_nodes",
      startWith: "$relatedEntityIds",
      connectFromField: "relatedEntityIds",
      connectToField: "_id",
      as: "connected",
      maxDepth: 2,
      depthField: "hops",
      restrictSearchWithMatch: { tenantId: <tenantId> }
  }},
  { $project: {
      name: 1,
      description: 1,
      content: 1,
      status: 1,
      tags: 1,
      metadata: 1,
      supersedes: 1,
      supersededBy: 1,
      connected: {
        _id: 1,
        name: 1,
        description: 1,
        status: 1,
        tags: 1,
        hops: 1
      }
  }}
])
```

### Expansion Behavior

Graph expansion is a separate query under the agent's control. After inspecting
hybrid search results, the orchestrator decides whether expansion adds value —
if results already answer the question, expansion is skipped. If results
reference other nodes that would provide useful context, the agent expands.

`maxDepth: 2` captures direct relationships (a node and its immediate neighbors)
and one transitive hop (a node's neighbor's neighbors). Beyond depth 2,
combinatorial explosion makes expansion impractical. The `depthField: "hops"`
annotation lets the agent weight context: `hops: 0` is the seed itself,
`hops: 1` is directly related, `hops: 2` is transitively related and weighted
lower.

With 10 seed documents at maxDepth 2, expansion typically yields 200–500
connected documents under tenant filtering. At ~2KB average (projected fields),
this stays well under MongoDB's 100MB per-stage memory limit.

---

## 5. Retrieval Quality

Retrieval is the load-bearing mechanism. With no deterministic conflict
detection, no typed routing, no category-driven filtering — the quality of what
surfaces from hybrid search and graph traversal IS the quality of Canon's
reasoning. If retrieval misses relevant knowledge, the orchestrator cannot
compensate. This section describes how the architecture maximizes retrieval
precision and recall.

### Quality by Design

**embeddingText is curated, not concatenated.** The `build_embedding_text`
function constructs a retrieval-optimized representation: identity header
(name + status), summary (description), semantic body (content capped at 1500
chars), and tags. This structure ensures the embedding captures organizational
identity and context — not raw noise. The status in the header means the
embedding space naturally clusters active vs. deprecated knowledge.

**Dual-modality fusion compensates for single-modality blindness.** Vector
search captures semantic equivalence ("retry logic" ≈ "exponential backoff").
Text search captures exact references ("billing-api", "ADR-042"). The 1.5:1.0
weight ratio reflects that most organizational queries are intent-based (vector-
favored), while exact-term precision is still rewarded. Neither modality alone
provides adequate recall.

**Tenant pre-filtering at the index level.** Both `$vectorSearch` and `$search`
pre-filter by `tenantId` BEFORE scoring. This isn't just multi-tenant isolation
— it means the scoring model only ranks within the relevant organizational
namespace. Cross-tenant noise never competes for relevance slots.

### Iterative Retrieval

The orchestrator is not limited to a single retrieval pass. If initial results
are sparse or off-target, the agent can:

1. **Reformulate and re-search** — construct a different query intent with
   different keywords or semantic framing
2. **Narrow with tags** — add tag-based filtering to the pipeline when broad
   search returns too much noise
3. **Expand from a single node** — if one result looks promising but others
   don't, graph-expand from that specific node only
4. **Follow supersession chains** — traverse `supersededBy` to find current
   versions of deprecated knowledge that surfaces in results

The semantic_retriever instruction does not limit the agent to one tool call.
The orchestrator can invoke it multiple times with different strategies — the
same way a human researcher would refine a search when the first results aren't
quite right.

### Relevance Signals Available Post-Retrieval

After retrieval, the orchestrator weighs results using signals that
`$rankFusion` alone cannot capture:

| Signal              | Interpretation                                                                  |
| ------------------- | ------------------------------------------------------------------------------- |
| `status`            | Active nodes are current truth; deprecated/resolved are historical              |
| `supersededBy`      | Node has been replaced — follow the chain for current state                     |
| `hops` (from graph) | 0 = seed, 1 = direct neighbor, 2 = transitive — weight decreases                |
| `updatedAt`         | Recency — recently modified nodes reflect current organizational state          |
| `tags`              | Semantic alignment — nodes sharing tags with the query context cluster together |
| Rank position       | `$rankFusion` score — higher position = stronger dual-modality match            |

The orchestrator's synthesis uses ALL of these signals holistically. A
deprecated node at rank 1 is still surfaced — but the orchestrator follows its
supersession chain to find what's current. A low-rank node at hops: 1 from a
high-rank seed may be more contextually relevant than a high-rank node with no
graph connection.

### Why This is Sufficient Without Deterministic Infrastructure

Previous architectures might use typed routing ("if intent mentions a service,
query the services table"), category-specific indexes, or deterministic conflict
detection rules. Canon replaces all of this with:

- **Semantic search that doesn't require the user to know what exists** — the
  embedding space captures equivalence regardless of how knowledge was
  originally categorized
- **Graph expansion that surfaces context the user didn't ask for** —
  relationships reveal organizational structure that keyword queries would miss
- **LLM reasoning that weighs heterogeneous evidence** — the orchestrator can
  synthesize across nodes of any kind, because it reads content and reasons
  about meaning, not about category labels

The tradeoff is explicit: retrieval quality depends on embedding quality (which
depends on `embeddingText` construction) and graph connectivity (which depends
on the memory_writer forming proper relationships at write time). Both are under
the agent's control.

---

## 6. Semantic Graph Evolution

The organizational memory graph is not static — knowledge evolves. Decisions get
revised, conventions get updated, approaches get replaced. Canon models this
evolution through first-class `supersedes`/`supersededBy` fields on each node,
backed by edges in `relatedEntityIds`.

### How Supersession Works

When a new decision replaces an old one:

1. The new node's `supersedes` field references the old node's `_id`
2. The old node's `supersededBy` field references the new node's `_id`
3. Both nodes carry each other in `relatedEntityIds` (bidirectional edge)
4. The old node's `status` transitions to `"deprecated"`

### Traversing Supersession Chains

```javascript
// From a deprecated decision, follow the chain to find what's current
db.memory_nodes.aggregate([
  { $match: { _id: <deprecated_node_id>, tenantId: <tenantId> } },
  { $graphLookup: {
      from: "memory_nodes",
      startWith: "$supersededBy",
      connectFromField: "supersededBy",
      connectToField: "_id",
      as: "successors",
      maxDepth: 3,
      depthField: "generation",
      restrictSearchWithMatch: { tenantId: <tenantId> }
  }}
])
```

This follows the supersession chain forward — from an old decision through each
revision to the currently active one. The `generation` field tells the
orchestrator how many iterations of evolution have occurred.

### How the Orchestrator Uses Supersession

The orchestrator understands what's current vs historical by reading the graph:

- A node with `status: "active"` and no `supersededBy` is current organizational
  truth
- A node with `status: "deprecated"` and a `supersededBy` reference is
  historical — it contains the rationale for a past approach and why it was
  abandoned
- A chain of supersessions reveals organizational evolution — how thinking
  changed over time

**Example:** An engineer asks about the deployment strategy for a service.
Hybrid search surfaces a deprecated decision about blue-green deployments. Graph
expansion follows `supersededBy` to a newer decision mandating canary
deployments. The orchestrator synthesizes both — explaining the current approach
(canary) and why the old approach (blue-green) was abandoned (too slow for the
team's release cadence).

### Why Deprecated Nodes Stay Searchable

Hybrid search may surface deprecated nodes when their semantic content closely
matches the query. This is intentional. Deprecated nodes contain institutional
memory about what was tried and what failed. A naive system would exclude them.
Canon surfaces them because the orchestrator can reason about the full
evolutionary arc — explaining not just what the current approach is, but why it
replaced the old one.

---

## 7. Organizational Reasoning

After retrieval and graph expansion surface relevant nodes, the orchestrator
reasons over the combined context. This is not a detection pipeline with
categorical outputs. It is the orchestrator applying intelligence to
organizational evidence.

### What the Orchestrator Sees

The orchestrator receives:

- **Hybrid search results** — nodes semantically and textually related to the
  intent, ranked by relevance
- **Graph-expanded context** — the neighborhood of those nodes, with hop
  distance indicating closeness
- **Supersession chains** — deprecated nodes and their replacements, revealing
  how knowledge evolved
- **Status signals** — which nodes are active, superseded, in-progress

### Reasoning Patterns

The orchestrator's reasoning emerges from the evidence. It is not constrained to
predefined categories. Examples of how it synthesizes:

**Identifying tensions between retrieved nodes:** "This intent proposes REST for
inter-service communication, but an active convention retrieved at hops: 1
mandates event-driven messaging for this service boundary."

**Recognizing historical context:** "A similar approach was tried last quarter
and caused an incident. The incident node at hops: 2 describes what went wrong.
The resolution node it links to describes the fix that was adopted."

**Surfacing superseded knowledge:** "The convention you're referencing was
superseded three months ago. The new version takes a different approach because
the original caused integration issues with the notification service."

**Connecting related organizational patterns:** "The service you're modifying is
owned by another team. The graph shows they recently completed a migration that
changes the API contract. Your proposed change may need coordination."

The orchestrator surfaces whatever from the retrieved context is relevant to the
engineer's intent — tensions, implications, historical context, related work,
coordination needs. The form of the response emerges from what the evidence
warrants. Real organizational tensions don't fit neatly into predefined
categories, and the orchestrator's synthesis needs to weigh multiple signals
holistically rather than report independent findings.

---

## 8. Why MongoDB is Load-Bearing

A mature Canon deployment accumulates hundreds of memory nodes with thousands of
edges. The agent cannot load everything into context — it must query
selectively. MongoDB provides four capabilities that make this retrieval
architecture possible:

### $rankFusion — Two Search Modalities

A pure vector store misses exact-term queries. A pure text index misses semantic
equivalence. `$rankFusion` combines both in a single pipeline without requiring
the application to merge result sets or maintain separate datastores.

### $graphLookup — Multi-Hop Traversal

`$graphLookup` expresses "follow relationships up to N hops" in a single
aggregation stage. This is critical for supersession chains, where traversal
must follow `supersededBy` across multiple generations, and for understanding
transitive organizational context (service → team → other services that team
owns).

### Pre-filtering by tenantId

Both `$vectorSearch` and `$search` stages pre-filter by tenantId at the index
level. No post-filtering waste, no separate databases per tenant, no risk of
cross-tenant data leakage in results.

### Single Collection Polymorphism

All organizational knowledge — decisions, conventions, incidents, migrations,
services, teams — lives in one collection. The agent searches across everything
in one query, then reasons over heterogeneity in context. Organizational memory
doesn't respect categorical boundaries, and neither should retrieval.

The combination enables the agent to answer questions that span semantic
similarity, exact terminology, graph relationships, and evolutionary history —
all within the MongoDB MCP tool's `aggregate` interface.
