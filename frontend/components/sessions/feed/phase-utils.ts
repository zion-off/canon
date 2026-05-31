import { z } from "zod";
import type { IdentifiedEvent, ToolCallPair, DisplayItem } from "@/lib/schemas/sessions";
import { EVENT_TYPE, DISPLAY_KIND, TOOL_NAME, AGENT_NAME } from "@/lib/constants";
import type { PhaseGroup, PhaseItem, CognitivePhase } from "./types";
import { COGNITIVE_PHASE, PHASE_ITEM_KIND } from "./types";
import { pairToolCallEvents } from "./pairToolCallEvents";

/**
 * Infer the cognitive phase for a given display item.
 */
function inferPhase(item: PhaseItem): CognitivePhase {
  switch (item.kind) {
    case PHASE_ITEM_KIND.THOUGHT:
      return COGNITIVE_PHASE.REASONING;
    case PHASE_ITEM_KIND.FINAL_RESPONSE:
      return COGNITIVE_PHASE.RESHAPING;
    case PHASE_ITEM_KIND.CONFIRMATION_REQUESTED:
    case PHASE_ITEM_KIND.CONFIRMATION_RECEIVED:
    case PHASE_ITEM_KIND.CANONIZE_PAIR:
      return COGNITIVE_PHASE.REMEMBERING;
    case PHASE_ITEM_KIND.SUBAGENT_GROUP: {
      if (item.group.agentName === AGENT_NAME.GRAPH_EXPLORER) return COGNITIVE_PHASE.TRACING;
      return COGNITIVE_PHASE.PERCEIVING;
    }
    case PHASE_ITEM_KIND.TOOL_PAIR: {
      const toolName = item.pair.started.payload.tool_name;
      if (toolName === TOOL_NAME.CANONIZE_NODE) return COGNITIVE_PHASE.REMEMBERING;
      if (toolName === TOOL_NAME.HYBRID_SEARCH) return COGNITIVE_PHASE.PERCEIVING;
      if (item.pair.started.author === AGENT_NAME.GRAPH_EXPLORER) return COGNITIVE_PHASE.TRACING;
      return COGNITIVE_PHASE.PERCEIVING;
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
        items.push({ kind: PHASE_ITEM_KIND.CANONIZE_PAIR, pair: di });
      } else {
        items.push({ kind: PHASE_ITEM_KIND.TOOL_PAIR, pair: di });
      }
    } else if (di.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
      items.push({ kind: PHASE_ITEM_KIND.SUBAGENT_GROUP, group: di });
    } else if (di.kind === DISPLAY_KIND.EVENT) {
      if (di.type === EVENT_TYPE.REASONING_CHECKPOINT) {
        items.push({ kind: PHASE_ITEM_KIND.THOUGHT, event: di });
      } else if (di.type === EVENT_TYPE.FINAL_RESPONSE) {
        items.push({ kind: PHASE_ITEM_KIND.FINAL_RESPONSE, event: di });
      } else if (di.type === EVENT_TYPE.CONFIRMATION_REQUESTED) {
        items.push({ kind: PHASE_ITEM_KIND.CONFIRMATION_REQUESTED, event: di });
      } else if (di.type === EVENT_TYPE.CONFIRMATION_RECEIVED) {
        items.push({ kind: PHASE_ITEM_KIND.CONFIRMATION_RECEIVED, event: di });
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

// ── Zod schemas for tool call args parsing ────────────────────────────────────

const hybridSearchResultSchema = z.object({
  count: z.number().int().optional(),
  results: z.array(z.record(z.unknown())).optional(),
}).passthrough();

const docWithNameSchema = z.object({ name: z.string().optional() }).passthrough();

const traceGraphResultSchema = z.object({
  count: z.number().int().optional(),
  nodes: z.array(z.unknown()).optional(),
}).passthrough();

const argsWithQuerySchema = z.object({ query: z.string().optional(), text: z.string().optional() }).passthrough();
const argsWithCollectionSchema = z.object({ collection: z.string().optional() }).passthrough();
const argsWithDocumentSchema = z.object({ document: z.record(z.unknown()).optional() }).passthrough();

/**
 * Generate a human-readable sentence for a tool call.
 */
export function toolCallSentence(pair: ToolCallPair): string {
  const toolName = pair.started.payload.tool_name;
  const args = pair.started.payload.args;
  const rawResult = pair.completed?.payload.result;

  switch (toolName) {
    case TOOL_NAME.HYBRID_SEARCH: {
      const argsParsed = argsWithQuerySchema.safeParse(args);
      const query = argsParsed.success ? (argsParsed.data.query ?? argsParsed.data.text ?? "memory") : "memory";
      let countStr = "";
      if (rawResult != null) {
        const resultParsed = hybridSearchResultSchema.safeParse(rawResult);
        if (resultParsed.success) {
          const count = resultParsed.data.count ?? resultParsed.data.results?.length;
          countStr = count != null ? ` — ${count} match${count === 1 ? "" : "es"}` : "";
        }
      }
      return `Searched organizational memory for "${truncate(query, 60)}"${countStr}`;
    }
    case TOOL_NAME.FIND: {
      const argsParsed = argsWithCollectionSchema.safeParse(args);
      const collection = argsParsed.success ? (argsParsed.data.collection ?? "nodes") : "nodes";
      return `Queried ${collection}`;
    }
    case TOOL_NAME.AGGREGATE: {
      return `Traversed relationships`;
    }
    case TOOL_NAME.COUNT: {
      const argsParsed = argsWithCollectionSchema.safeParse(args);
      const collection = argsParsed.success ? (argsParsed.data.collection ?? "nodes") : "nodes";
      return `Counted ${collection} records`;
    }
    case TOOL_NAME.CANONIZE_NODE: {
      const argsParsed = argsWithDocumentSchema.safeParse(args);
      let name: string | undefined;
      if (argsParsed.success && argsParsed.data.document) {
        const docParsed = docWithNameSchema.safeParse(argsParsed.data.document);
        name = docParsed.success ? docParsed.data.name : undefined;
      }
      return name ? `Forming memory: "${truncate(name, 50)}"` : "Forming new memory node";
    }
    default: {
      if (toolName === "trace_graph") {
        let count: number | undefined;
        if (rawResult != null) {
          const resultParsed = traceGraphResultSchema.safeParse(rawResult);
          if (resultParsed.success) {
            count = resultParsed.data.count ?? resultParsed.data.nodes?.length;
          }
        }
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
