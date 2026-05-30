import type { IdentifiedEvent, ToolCallPair, DisplayItem } from "@/lib/schemas/sessions";
import { EVENT_TYPE, DISPLAY_KIND, TOOL_NAME, AGENT_NAME } from "@/lib/constants";
import type { PhaseGroup, PhaseItem, CognitivePhase } from "./types";
import { pairToolCallEvents } from "./pairToolCallEvents";

/**
 * Infer the cognitive phase for a given display item.
 */
function inferPhase(item: PhaseItem): CognitivePhase {
  switch (item.kind) {
    case "thought":
      return "reasoning";
    case "final-response":
      return "reshaping";
    case "confirmation-requested":
    case "confirmation-received":
    case "canonize-pair":
      return "remembering";
    case "subagent-group": {
      if (item.group.agentName === AGENT_NAME.GRAPH_EXPLORER) return "tracing";
      return "perceiving";
    }
    case "tool-pair": {
      const toolName = item.pair.started.payload.tool_name;
      if (toolName === TOOL_NAME.CANONIZE_NODE) return "remembering";
      if (toolName === TOOL_NAME.HYBRID_SEARCH) return "perceiving";
      if (item.pair.started.author === AGENT_NAME.GRAPH_EXPLORER) return "tracing";
      return "perceiving";
    }
  }
}

/**
 * Convert flat display items into phase items.
 */
function toPhaseItems(displayItems: DisplayItem[]): PhaseItem[] {
  const items: PhaseItem[] = [];

  for (const di of displayItems) {
    if (di.kind === DISPLAY_KIND.TOOL_CALL_PAIR) {
      if (di.started.payload.tool_name === TOOL_NAME.CANONIZE_NODE) {
        items.push({ kind: "canonize-pair", pair: di });
      } else {
        items.push({ kind: "tool-pair", pair: di });
      }
    } else if (di.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
      items.push({ kind: "subagent-group", group: di });
    } else if ("type" in di) {
      if (di.type === EVENT_TYPE.REASONING_CHECKPOINT) {
        items.push({ kind: "thought", event: di as IdentifiedEvent & { type: "reasoning_checkpoint" } });
      } else if (di.type === EVENT_TYPE.FINAL_RESPONSE) {
        items.push({ kind: "final-response", event: di as IdentifiedEvent & { type: "final_response" } });
      } else if (di.type === EVENT_TYPE.CONFIRMATION_REQUESTED) {
        items.push({ kind: "confirmation-requested", event: di as IdentifiedEvent & { type: "confirmation_requested" } });
      } else if (di.type === EVENT_TYPE.CONFIRMATION_RECEIVED) {
        items.push({ kind: "confirmation-received", event: di as IdentifiedEvent & { type: "confirmation_received" } });
      }
    }
  }

  return items;
}

/**
 * Group phase items into sequential phase groups.
 * Consecutive items of the same phase are merged into one group.
 */
function groupByPhase(items: PhaseItem[]): PhaseGroup[] {
  const groups: PhaseGroup[] = [];

  for (const item of items) {
    const phase = inferPhase(item);
    const lastGroup = groups[groups.length - 1];

    if (lastGroup && lastGroup.phase === phase) {
      lastGroup.items.push(item);
    } else {
      groups.push({ phase, items: [item] });
    }
  }

  return groups;
}

/**
 * Main function: takes raw identified events for a run and produces
 * phased groups for rendering.
 */
export function buildPhaseGroups(events: IdentifiedEvent[]): PhaseGroup[] {
  const visibleEvents = events.filter(
    (e) => e.type !== EVENT_TYPE.RUN_STARTED && e.type !== EVENT_TYPE.RUN_COMPLETED,
  );
  const displayItems = pairToolCallEvents(visibleEvents);
  const phaseItems = toPhaseItems(displayItems);
  return groupByPhase(phaseItems);
}

/**
 * Compute real latency between tool_call_started and tool_call_completed.
 */
export function computeLatencyMs(pair: ToolCallPair): number | null {
  if (!pair.started.timestamp || !pair.completed?.timestamp) return null;
  const start = new Date(pair.started.timestamp).getTime();
  const end = new Date(pair.completed.timestamp).getTime();
  const diff = end - start;
  return diff >= 0 ? diff : null;
}

/**
 * Format latency for display.
 */
export function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Generate a human-readable sentence for a tool call.
 */
export function toolCallSentence(pair: ToolCallPair): string {
  const toolName = pair.started.payload.tool_name;
  const args = pair.started.payload.args;
  const result = pair.completed?.payload.result as Record<string, unknown> | undefined;

  switch (toolName) {
    case TOOL_NAME.HYBRID_SEARCH: {
      const query = (args.query as string) ?? (args.text as string) ?? "memory";
      const count = (result?.count as number) ?? (result?.results as unknown[] | undefined)?.length;
      const countStr = count != null ? `${count} match${count === 1 ? "" : "es"}` : "";
      return `Searched organizational memory for "${truncate(query, 60)}"${countStr ? ` — ${countStr}` : ""}`;
    }
    case TOOL_NAME.FIND: {
      const collection = (args.collection as string) ?? "nodes";
      return `Queried ${collection}`;
    }
    case TOOL_NAME.AGGREGATE: {
      return `Traversed relationships`;
    }
    case TOOL_NAME.COUNT: {
      const collection = (args.collection as string) ?? "nodes";
      return `Counted ${collection} records`;
    }
    case TOOL_NAME.CANONIZE_NODE: {
      const name = (args.document as Record<string, unknown>)?.name as string | undefined;
      return name ? `Forming memory: "${truncate(name, 50)}"` : "Forming new memory node";
    }
    default: {
      // trace_graph or unknown
      if (toolName === "trace_graph") {
        const count = (result?.count as number) ?? (result?.nodes as unknown[] | undefined)?.length;
        return `Traced relationships${count ? ` — impact across ${count} nodes` : ""}`;
      }
      return toolName.replace(/_/g, " ");
    }
  }
}

function truncate(str: string, max: number): string {
  if (str.length <= max) return str;
  return str.slice(0, max - 1) + "…";
}
