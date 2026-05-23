# 04 — Memory Graph

## Purpose

The memory graph page visualizes the organization's living semantic knowledge
graph — the same structure Canon's agent reasons over. It makes organizational
cognition tangible: you can see what Canon knows, how knowledge connects, where
the graph is growing, and how understanding has evolved through supersession.

This is not a database admin view. It is a cognitive map of the organization's
accumulated knowledge — decisions, constraints, patterns, and the relationships
between them, rendered as a living, interactive graph.

---

## Data Source

At hackathon/demo scale (hundreds of nodes), the frontend queries the full
organizational graph in a single request via a server action.

```typescript
// Server action (lib/actions/graph.ts)
import { getGraph } from "@/lib/actions/graph";

const graphData = await getGraph();
```

The server action calls the backend's `/api/v1/graph` endpoint (tenant derived
from JWT), which queries `memory_nodes` with a projection excluding `embedding`
and `content` (large, unnecessary for visualization), and transforms the result
into the graph format described below.

### Graph Transformation

The API route transforms MongoDB documents into the graph library's format:

```typescript
interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface GraphNode {
  id: string;
  name: string;
  description: string;
  status: string;
  tags: string[];
  supersedes: string | null;
  supersededBy: string | null;
  updatedAt: string;
  createdAt: string;
  connections: number; // Computed client-side: count of links touching this node
}

interface GraphLink {
  source: string;
  target: string;
  type: "related" | "supersedes";
}
```

Links are derived from two sources:

1. `relatedEntityIds` → links with `type: "related"`
2. `supersedes` → link with `type: "supersedes"` (directional: old → new)

Since `relatedEntityIds` are bidirectional, deduplicate by always using the
lexicographically smaller ID as `source`.

---

## Visualization

### Library

`react-force-graph-2d` — a React component wrapping D3's force simulation.
Lightweight, performant at hackathon scale, renders to Canvas for smooth
interaction.

### Node Rendering

Nodes encode organizational meaning through visual properties:

| Property    | Encoding                                                                                        |
| ----------- | ----------------------------------------------------------------------------------------------- |
| **Color**   | Derived from `status`: active = vibrant, deprecated = faded, in_progress = pulsing              |
| **Size**    | Proportional to connectivity — nodes with more edges are larger (more organizationally central) |
| **Label**   | `name` field, rendered below node. Truncated at ~30 chars.                                      |
| **Opacity** | Deprecated/superseded nodes rendered at reduced opacity                                         |

#### Status Color Map

| Status        | Color           | Meaning                         |
| ------------- | --------------- | ------------------------------- |
| `active`      | Blue (#3B82F6)  | Current organizational truth    |
| `in_progress` | Amber (#F59E0B) | Knowledge being formed          |
| `deprecated`  | Gray (#9CA3AF)  | Superseded — historical context |
| `resolved`    | Green (#10B981) | Completed, still relevant       |
| `completed`   | Green (#10B981) | Same as resolved                |
| other         | Slate (#64748B) | Unrecognized status             |

### Edge Rendering

| Edge Type    | Visual                                                                      |
| ------------ | --------------------------------------------------------------------------- |
| `related`    | Thin gray line. Represents organizational association.                      |
| `supersedes` | Dashed directional line (arrow). Old → new. Represents knowledge evolution. |

Supersession edges are visually distinct — they tell the story of how
organizational understanding evolved.

### Interaction

| Action      | Behavior                                             |
| ----------- | ---------------------------------------------------- |
| Hover node  | Tooltip with `name`, `description`, `status`, `tags` |
| Click node  | Side panel with full detail (see below)              |
| Drag node   | Repositions node in force simulation                 |
| Scroll      | Zoom in/out                                          |
| Drag canvas | Pan                                                  |

### Node Detail Panel

Clicking a node opens a side panel showing:

```
┌──────────────────────────────┐
│  Use event sourcing for      │
│  order service               │
│                              │
│  Status: active              │
│  Tags: decision, arch...     │
│                              │
│  ADR-042: Adopt event        │
│  sourcing pattern for order  │
│  lifecycle management...     │
│                              │
│  Connected to:               │
│  • order-service (active)    │
│  • billing-api (active)      │
│  • INC-2025-017 (resolved)   │
│                              │
│  Supersedes: (none)          │
│  Superseded by: (none)       │
│                              │
│  Created: Sep 15, 2024       │
│  Updated: Sep 15, 2024       │
└──────────────────────────────┘
```

Connected nodes are clickable — clicking one pans the graph to that node and
opens its detail panel.

---

## Visual Identity

The graph should feel like a living cognitive map, not a network diagram.

### Force Simulation Parameters

```typescript
<ForceGraph2D
  graphData={data}
  nodeRelSize={4}
  linkDirectionalArrowLength={link => link.type === "supersedes" ? 6 : 0}
  linkLineDash={link => link.type === "supersedes" ? [4, 2] : null}
  linkColor={() => "rgba(148, 163, 184, 0.3)"}
  nodeCanvasObject={renderNode}
  cooldownTicks={100}
  d3AlphaDecay={0.02}
  d3VelocityDecay={0.3}
  d3ForceConfig={{
    charge: { strength: -120 },
    link: { distance: 80 },
  }}
/>
```

### Semantic Clustering

The force simulation naturally clusters densely connected subgraphs. Nodes that
share many `relatedEntityIds` gravitate together — this creates visual semantic
neighborhoods. A cluster of nodes around a service reveals organizational
context around that service. A chain of superseded nodes shows knowledge
evolution as a visible path.

No explicit clustering algorithm is needed — D3's force simulation with charge
repulsion and link attraction produces meaningful spatial grouping from the
graph's natural structure.

### Active Regions

Recently modified nodes (`updatedAt` within the last 7 days) receive a subtle
glow or ring effect — making the "active regions" of organizational memory
visible at a glance. This shows where the organization is currently learning and
evolving.

```typescript
function renderNode(node, ctx, globalScale) {
  const isRecent =
    Date.now() - new Date(node.updatedAt).getTime() < 7 * 86400000;
  const radius = Math.sqrt(node.connections + 1) * 4;

  if (isRecent) {
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius + 3, 0, 2 * Math.PI);
    ctx.fillStyle = "rgba(59, 130, 246, 0.15)";
    ctx.fill();
  }

  ctx.beginPath();
  ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = statusColor(node.status, node.supersededBy);
  ctx.fill();

  // Label
  if (globalScale > 0.7) {
    ctx.font = `${11 / globalScale}px sans-serif`;
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
    ctx.fillText(
      node.name.slice(0, 30),
      node.x,
      node.y + radius + 10 / globalScale,
    );
  }
}
```

### Supersession Chains

When a node has `supersededBy`, the graph shows the evolutionary chain visually
— deprecated nodes fade to gray, connected by dashed directional arrows to their
successors. Following a supersession chain through the graph reveals how
organizational thinking evolved: "We used to do X, then switched to Y because of
Z, then refined Y into W."

This visual pattern reinforces Canon's core value: the organization doesn't lose
context. Past decisions and their reasoning remain in the graph as historical
context, connected to their successors.

---

## Page Layout

```
┌──────────────────────────────────────────────────────────┐
│  Canon                       [Dashboard] [Settings] [◉]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Organizational Memory                                   │
│  142 nodes · 387 relationships                           │
│                                                          │
│  ┌─ Filters ──────────────────────────────────────────┐  │
│  │ Status: [All ▼]  Tags: [___________]  Search: [__] │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────┬───────────────┐  │
│  │                                    │               │  │
│  │                                    │  Node Detail  │  │
│  │         Force Graph                │  Panel        │  │
│  │         (canvas)                   │  (on click)   │  │
│  │                                    │               │  │
│  │                                    │               │  │
│  │                                    │               │  │
│  └────────────────────────────────────┴───────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Filters

Client-side filtering — the full graph is loaded, filters hide/show nodes:

| Filter | Behavior                                                            |
| ------ | ------------------------------------------------------------------- |
| Status | Dropdown: All, Active, Deprecated, In Progress, Resolved, Completed |
| Tags   | Text input, autocomplete from all tags in the dataset               |
| Search | Fuzzy match on `name` — highlights matching nodes                   |

Filtering by status or tags removes non-matching nodes and their edges from the
force simulation. The graph re-settles to show only the filtered subset.

Search highlights matching nodes (brighter color, larger radius) without
removing other nodes — preserving spatial context.

---

## Performance

At hackathon scale (< 1000 nodes, < 5000 edges), the full-graph approach is
viable:

- Initial query: single MongoDB `find` with projection (~200KB for 500 nodes)
- Canvas rendering: `react-force-graph-2d` handles thousands of nodes smoothly
- Client-side filtering: no re-fetching needed

For production scale, consider: pagination, viewport-based loading, server-side
clustering, or WebGL rendering (react-force-graph-3d). Out of scope for now.
