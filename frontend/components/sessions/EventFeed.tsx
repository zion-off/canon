"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import type { AgentEvent, IdentifiedEvent } from "@/lib/schemas/sessions";
import { useEventStream } from "@/hooks/useEventStream";
import { RunGroup } from "./RunGroup";
import { EVENT_TYPE, DISPLAY_KIND } from "@/lib/constants";

interface EventFeedProps {
  sessionId: string;
  initialEvents: AgentEvent[];
  isLive: boolean;
}

interface RunBucket {
  runId: string;
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
}

function groupEventsIntoRuns(events: IdentifiedEvent[]): RunBucket[] {
  const buckets = new Map<string, IdentifiedEvent[]>();

  for (const event of events) {
    const key = event.runId;
    const existing = buckets.get(key);
    if (existing) {
      existing.push(event);
    } else {
      buckets.set(key, [event]);
    }
  }

  return Array.from(buckets.entries()).map(([runId, runEvents], index) => ({
    runId,
    runIndex: index + 1,
    events: runEvents,
    timestamp:
      runEvents.find((e) => e.type === EVENT_TYPE.RUN_STARTED)?.timestamp ??
      runEvents[0]?.timestamp ??
      null,
  }));
}

function toIdentifiedEvent(event: AgentEvent, stableId: number): IdentifiedEvent {
  return { ...event, kind: DISPLAY_KIND.EVENT, stableId };
}

export function EventFeed({ sessionId, initialEvents, isLive }: EventFeedProps) {
  const stableIdRef = useRef(initialEvents.length);
  const assignId = useCallback((event: AgentEvent): IdentifiedEvent => {
    return toIdentifiedEvent(event, stableIdRef.current++);
  }, []);

  const [events, setEvents] = useState<IdentifiedEvent[]>(() =>
    initialEvents.map((e, i) => toIdentifiedEvent(e, i)),
  );
  const feedEndRef = useRef<HTMLDivElement>(null);
  const [live, setLive] = useState(isLive);

  const handleNewEvent = useCallback(
    (event: AgentEvent) => {
      setEvents((prev) => [...prev, assignId(event)]);
      if (event.type === EVENT_TYPE.RUN_STARTED) {
        setLive(true);
      }
      if (event.type === EVENT_TYPE.RUN_COMPLETED) {
        setLive(false);
      }
    },
    [assignId],
  );

  const initialMaxSeq = useMemo(
    () => Math.max(0, ...initialEvents.map((e) => e.sequence ?? 0)),
    [initialEvents],
  );

  useEventStream(sessionId, handleNewEvent, true, initialMaxSeq);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const runs = groupEventsIntoRuns(events);

  if (events.length === 0) {
    return (
      <div className="border-b border-canon-border px-6 py-12 text-center">
        <p className="text-canon-text-secondary">
          No events recorded yet. Events will appear here when the session receives activity.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {live && (
        <div className="flex items-center gap-2 pb-2">
          <span className="inline-block h-2 w-2 bg-canon-success" />
          <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-success">
            Live
          </span>
        </div>
      )}

      {runs.map((run) => (
        <RunGroup
          key={run.runId}
          runIndex={run.runIndex}
          events={run.events}
          timestamp={run.timestamp}
        />
      ))}

      <div ref={feedEndRef} />
    </div>
  );
}
