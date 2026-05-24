"use client";

import type { IdentifiedEvent } from "./EventFeed";
import { EventItem } from "./EventItem";

interface RunGroupProps {
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
}

function formatRunTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function RunGroup({ runIndex, events, timestamp }: RunGroupProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 pb-1 pt-4">
        <span className="text-sm font-medium text-canon-text">
          Run {runIndex}
        </span>
        {timestamp && (
          <>
            <span className="text-canon-muted">·</span>
            <span className="text-xs text-canon-muted">
              {formatRunTime(timestamp)}
            </span>
          </>
        )}
      </div>

      <div className="space-y-2 border-l border-canon-border pl-4">
        {events.map((event) => (
          <EventItem key={event.stableId} event={event} />
        ))}
      </div>
    </div>
  );
}
