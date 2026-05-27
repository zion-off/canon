import type {
  IdentifiedEvent,
  DisplayItem,
  ToolCallPair,
  SubagentGroup,
} from "@/lib/schemas/sessions";
import { EVENT_TYPE, DISPLAY_KIND, TOOL_NAME, SUBAGENT_TOOL_NAMES } from "@/lib/constants";
import type { PairLocation } from "./types";

// Builds the display item list from a flat sequence of identified events:
// - subagent_invoked events become SubagentGroup containers
// - tool_call_started/completed pairs for subagent tools nest inside their group
// - outer AgentTool wrapper calls (tool_name matches a subagent name) are filtered out
// - emit_checkpoint tool pairs are filtered out (surfaced as ReasoningCheckpoint events)
// - all other events pass through unchanged
export function pairToolCallEvents(events: IdentifiedEvent[]): DisplayItem[] {
  const result: DisplayItem[] = [];
  const pendingGroups = new Map<string, number>(); // agentInvocationId → result idx
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
      };
      pendingGroups.set(event.payload.agent_invocation_id, result.length);
      result.push(group);
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
        const group = result[groupIdx] as SubagentGroup;
        const pairIdx = group.toolPairs.length;
        group.toolPairs.push(pair);
        pendingPairs.set(event.payload.invocation_id, { kind: "in-group", groupIdx, pairIdx });
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
        const existing = result[location.idx] as ToolCallPair;
        result[location.idx] = { ...existing, completed: event };
      } else {
        const group = result[location.groupIdx] as SubagentGroup;
        group.toolPairs[location.pairIdx] = {
          ...group.toolPairs[location.pairIdx],
          completed: event,
        };
      }
      pendingPairs.delete(event.payload.invocation_id);
    } else {
      result.push(event);
    }
  }

  return result;
}
