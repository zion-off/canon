"use client";

import type { IdentifiedEvent, DisplayItem, ToolCallPair } from "@/lib/schemas/sessions";
import { EventItem } from "./EventItem";
import { formatDateTime } from "@/lib/date-utils";
import { EVENT_TYPE, DISPLAY_KIND, TOOL_NAME } from "@/lib/constants";

interface RunGroupProps {
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
}

// Pairs tool_call_started and tool_call_completed events that share an invocation_id
// into a single ToolCallPair display item. All other events pass through unchanged.
function pairToolCallEvents(events: IdentifiedEvent[]): DisplayItem[] {
  const result: DisplayItem[] = [];
  // Maps invocation_id -> index in result where the in-progress pair lives
  const pendingPairs = new Map<string, number>();

  for (const event of events) {
    if (event.type === EVENT_TYPE.TOOL_CALL_STARTED) {
      if (event.payload.tool_name === TOOL_NAME.EMIT_CHECKPOINT) continue;
      const pair: ToolCallPair = {
        kind: DISPLAY_KIND.TOOL_CALL_PAIR,
        stableId: event.stableId,
        invocationId: event.payload.invocation_id,
        started: event,
        completed: null,
      };
      pendingPairs.set(event.payload.invocation_id, result.length);
      result.push(pair);
    } else if (event.type === EVENT_TYPE.TOOL_CALL_COMPLETED) {
      if (event.payload.tool_name === TOOL_NAME.EMIT_CHECKPOINT) continue;
      const idx = pendingPairs.get(event.payload.invocation_id);
      if (idx !== undefined) {
        const existing = result[idx] as ToolCallPair;
        result[idx] = { ...existing, completed: event };
        pendingPairs.delete(event.payload.invocation_id);
      } else {
        // Orphaned completed event with no matching started — render it standalone
        result.push(event);
      }
    } else {
      result.push(event);
    }
  }

  return result;
}

export function RunGroup({ runIndex, events, timestamp }: RunGroupProps) {
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
        {displayItems.map((item) => (
          <EventItem key={item.stableId} item={item} />
        ))}
      </div>
    </div>
  );
}
