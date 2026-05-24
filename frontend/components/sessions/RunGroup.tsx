"use client";

import type { IdentifiedEvent } from "./EventFeed";
import { EventItem } from "./EventItem";
import { formatDateTime } from "@/lib/date-utils";
import { EVENT_TYPE } from "@/lib/constants";

interface RunGroupProps {
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
}

export function RunGroup({ runIndex, events, timestamp }: RunGroupProps) {
  const visibleEvents = events.filter((e) => e.type !== EVENT_TYPE.RUN_STARTED);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 pb-1 pt-4">
        <span className="text-sm font-medium text-canon-text">Run {runIndex}</span>
        {timestamp && (
          <>
            <span className="text-canon-muted">·</span>
            <span className="text-xs text-canon-muted">{formatDateTime(timestamp)}</span>
          </>
        )}
      </div>

      <div className="space-y-2 border-l border-canon-border pl-4">
        {visibleEvents.map((event) => (
          <EventItem key={event.stableId} event={event} />
        ))}
      </div>
    </div>
  );
}
