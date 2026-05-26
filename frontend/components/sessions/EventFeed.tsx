"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { AgentEvent } from "@/lib/schemas/sessions";
import { useEventStream } from "@/hooks/useEventStream";
import { RunGroup } from "./RunGroup";
import { EVENT_TYPE } from "@/lib/constants";

interface EventFeedProps {
  sessionId: string;
  initialEvents: AgentEvent[];
  isLive: boolean;
}

export interface IdentifiedEvent extends AgentEvent {
  stableId: number;
}

interface RunBucket {
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
}

function groupEventsIntoRuns(events: IdentifiedEvent[]): RunBucket[] {
  const runs: RunBucket[] = [];
  let currentRun: IdentifiedEvent[] = [];
  let runCounter = 0;
  let currentTimestamp: string | null = null;

  for (const event of events) {
    if (event.type === EVENT_TYPE.RUN_STARTED) {
      if (currentRun.length > 0) {
        runs.push({ runIndex: runCounter, events: currentRun, timestamp: currentTimestamp });
      }
      runCounter++;
      currentTimestamp = event.timestamp;
      currentRun = [event];
    } else {
      if (runCounter === 0) {
        runCounter = 1;
        currentTimestamp = event.timestamp;
      }
      currentRun.push(event);
    }
  }

  if (currentRun.length > 0) {
    runs.push({ runIndex: runCounter, events: currentRun, timestamp: currentTimestamp });
  }

  return runs;
}

export function EventFeed({ sessionId, initialEvents, isLive }: EventFeedProps) {
  const stableIdRef = useRef(initialEvents.length);
  const assignId = useCallback((event: AgentEvent): IdentifiedEvent => {
    return { ...event, stableId: stableIdRef.current++ };
  }, []);

  const [events, setEvents] = useState<IdentifiedEvent[]>(() =>
    initialEvents.map((e, i) => ({ ...e, stableId: i })),
  );
  const feedEndRef = useRef<HTMLDivElement>(null);
  const [live, setLive] = useState(isLive);

  const handleNewEvent = useCallback(
    (event: AgentEvent) => {
      setEvents((prev) => [...prev, assignId(event)]);
      if (event.type === EVENT_TYPE.RUN_COMPLETED) {
        setLive(false);
      }
    },
    [assignId],
  );

  useEventStream(sessionId, handleNewEvent, live);

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
          key={run.runIndex}
          runIndex={run.runIndex}
          events={run.events}
          timestamp={run.timestamp}
        />
      ))}

      <div ref={feedEndRef} />
    </div>
  );
}
