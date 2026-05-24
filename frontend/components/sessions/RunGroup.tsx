"use client";

import type { AgentEvent } from "@/lib/schemas/sessions";
import { EventItem } from "./EventItem";

interface RunGroupProps {
  runIndex: number;
  events: AgentEvent[];
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
        <span className="text-sm font-medium text-slate-300">
          Run {runIndex}
        </span>
        {timestamp && (
          <>
            <span className="text-slate-600">·</span>
            <span className="text-xs text-slate-500">
              {formatRunTime(timestamp)}
            </span>
          </>
        )}
      </div>

      <div className="space-y-2 border-l border-white/[0.06] pl-4">
        {events.map((event, idx) => (
          <EventItem key={`${event.sequence ?? idx}-${event.type}`} event={event} />
        ))}
      </div>
    </div>
  );
}
