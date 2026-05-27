"use client";

import type {
  IdentifiedEvent,
  DisplayItem,
  ToolCallPair,
  SubagentGroup,
} from "@/lib/schemas/sessions";
import { EventItem } from "./EventItem";
import { formatDateTime } from "@/lib/date-utils";
import { EVENT_TYPE, DISPLAY_KIND, TOOL_NAME, SUBAGENT_TOOL_NAMES } from "@/lib/constants";

interface RunGroupProps {
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
  invocationArgs: { request: string; context: string } | null;
}

type PairLocation =
  | { kind: "top-level"; idx: number }
  | { kind: "in-group"; groupIdx: number; pairIdx: number };

// Builds the display item list from a flat sequence of identified events:
// - subagent_invoked events become SubagentGroup containers
// - tool_call_started/completed pairs for subagent tools nest inside their group
// - outer AgentTool wrapper calls (tool_name matches a subagent name) are filtered out
// - emit_checkpoint tool pairs are filtered out (surfaced as ReasoningCheckpoint events)
// - all other events pass through unchanged
function pairToolCallEvents(events: IdentifiedEvent[]): DisplayItem[] {
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

export function RunGroup({ runIndex, events, timestamp, invocationArgs }: RunGroupProps) {
  const visibleEvents = events.filter((e) => e.type !== EVENT_TYPE.RUN_STARTED);
  const displayItems = pairToolCallEvents(visibleEvents);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 pb-1 pt-4">
        <span className="text-sm font-medium text-canon-text">Run {runIndex}</span>
        {timestamp && (
          <>
            <span className="text-canon-text-secondary">·</span>
            <span suppressHydrationWarning className="text-xs text-canon-text-secondary">
              {formatDateTime(timestamp)}
            </span>
          </>
        )}
      </div>

      <div className="space-y-2 border-l border-canon-border pl-4">
        {invocationArgs && (
          <div className="flex gap-3">
            <div className="pt-1">
              <div className="w-2 h-2 rounded-full bg-canon-accent shrink-0" />
            </div>
            <div className="pb-1 min-w-0 flex-1">
              <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
                Harness Request
              </span>
              <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-canon-text-secondary">
                {JSON.stringify(invocationArgs, null, 2)}
              </pre>
            </div>
          </div>
        )}
        {displayItems.map((item) => (
          <EventItem key={item.stableId} item={item} />
        ))}
      </div>
    </div>
  );
}
