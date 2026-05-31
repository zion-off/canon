import type {
  IdentifiedEvent,
  DisplayItem,
  ToolCallPair,
  SubagentGroup,
} from "@/lib/schemas/sessions";
import { EVENT_TYPE, DISPLAY_KIND, TOOL_NAME, SUBAGENT_TOOL_NAMES, AGENT_NAME } from "@/lib/constants";

type PairLocation =
  | { kind: "top-level"; idx: number }
  | { kind: "in-group"; groupIdx: number; pairIdx: number };

const SUBAGENT_NAMES: Set<string> = new Set([AGENT_NAME.SEMANTIC_RETRIEVER, AGENT_NAME.GRAPH_EXPLORER]);


// Builds the display item list from a flat sequence of identified events:
// - subagent_invoked events become SubagentGroup containers
// - tool_call_started/completed pairs for subagent tools nest inside their group
// - reasoning_checkpoint events from subagent authors are routed into their active group
// - outer AgentTool wrapper calls (tool_name matches a subagent name) are filtered out
// - emit_checkpoint tool pairs are filtered out (surfaced as ReasoningCheckpoint events)
// - all other events pass through unchanged
export function pairToolCallEvents(events: IdentifiedEvent[]): DisplayItem[] {
  const result: DisplayItem[] = [];
  const pendingGroups = new Map<string, number>(); // agentInvocationId → result idx
  // Track the most recently opened group per agentName for checkpoint routing
  const activeGroupByAgentName = new Map<string, number>(); // agentName → result idx
  const pendingPairs = new Map<string, PairLocation>(); // invocationId → location

  for (const event of events) {
    if (event.type === EVENT_TYPE.SUBAGENT_INVOKED) {
      const group: SubagentGroup = {
        kind: DISPLAY_KIND.SUBAGENT_GROUP,
        stableId: event.stableId,
        agentInvocationId: event.payload.agent_invocation_id,
        agentName: event.payload.agent_name,
        timestamp: event.timestamp,
        toolPairs: [],
        checkpoints: [],
      };
      const idx = result.length;
      pendingGroups.set(event.payload.agent_invocation_id, idx);
      activeGroupByAgentName.set(event.payload.agent_name, idx);
      result.push(group);
    } else if (event.type === EVENT_TYPE.REASONING_CHECKPOINT) {
      const author = event.author;
      if (author && SUBAGENT_NAMES.has(author)) {
        const groupIdx = activeGroupByAgentName.get(author);
        if (groupIdx !== undefined) {
          const item = result[groupIdx];
          if (item !== undefined && item.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
            item.checkpoints = [...item.checkpoints, event];
            continue;
          }
        }
      }
      result.push(event);
    } else if (event.type === EVENT_TYPE.TOOL_CALL_STARTED) {
      if (
        event.payload.tool_name === TOOL_NAME.EMIT_CHECKPOINT ||
        SUBAGENT_TOOL_NAMES.has(event.payload.tool_name)
      )
        continue;

      const pair: ToolCallPair = {
        kind: DISPLAY_KIND.TOOL_CALL_PAIR,
        stableId: event.stableId,
        invocationId: event.payload.invocation_id,
        started: event,
        completed: null,
      };

      const agentInvId = event.payload.agent_invocation_id;
      const groupIdx = agentInvId != null ? pendingGroups.get(agentInvId) : undefined;

      if (groupIdx !== undefined) {
        const item = result[groupIdx];
        if (item !== undefined && item.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
          const pairIdx = item.toolPairs.length;
          item.toolPairs.push(pair);
          pendingPairs.set(event.payload.invocation_id, { kind: "in-group", groupIdx, pairIdx });
        }
      } else {
        pendingPairs.set(event.payload.invocation_id, { kind: "top-level", idx: result.length });
        result.push(pair);
      }
    } else if (event.type === EVENT_TYPE.TOOL_CALL_COMPLETED) {
      if (
        event.payload.tool_name === TOOL_NAME.EMIT_CHECKPOINT ||
        SUBAGENT_TOOL_NAMES.has(event.payload.tool_name)
      )
        continue;

      const location = pendingPairs.get(event.payload.invocation_id);
      if (location === undefined) continue;

      if (location.kind === "top-level") {
        const item = result[location.idx];
        if (item !== undefined && item.kind === DISPLAY_KIND.TOOL_CALL_PAIR) {
          result[location.idx] = { ...item, completed: event };
        }
      } else {
        const item = result[location.groupIdx];
        if (item !== undefined && item.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
          item.toolPairs[location.pairIdx] = {
            ...item.toolPairs[location.pairIdx],
            completed: event,
          };
        }
      }
      pendingPairs.delete(event.payload.invocation_id);
    } else {
      result.push(event);
    }
  }

  return result;
}
