"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { AnimatePresence, motion, MotionConfig } from "motion/react";
import type { AgentEvent, IdentifiedEvent } from "@/lib/schemas/sessions";
import { useEventStream } from "@/hooks/useEventStream";
import { useReducedMotion } from "@/hooks/useReducedMotion";
import { EVENT_TYPE, DISPLAY_KIND } from "@/lib/constants";
import { RunGroup } from "./RunGroup";

interface EventFeedProps {
  sessionId: string;
  initialEvents: AgentEvent[];
  isLive: boolean;
}

interface RunBucket {
  runId: string;
  events: IdentifiedEvent[];
}

function toIdentifiedEvent(event: AgentEvent, stableId: number): IdentifiedEvent {
  return { ...event, kind: DISPLAY_KIND.EVENT, stableId } as IdentifiedEvent;
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
  return Array.from(buckets.entries()).map(([runId, runEvents]) => ({ runId, events: runEvents }));
}

export function EventFeed({ sessionId, initialEvents, isLive }: EventFeedProps) {
  const reducedMotion = useReducedMotion();
  const stableIdRef = useRef(initialEvents.length);
  const assignId = useCallback(
    (event: AgentEvent): IdentifiedEvent => toIdentifiedEvent(event, stableIdRef.current++),
    [],
  );

  const [events, setEvents] = useState<IdentifiedEvent[]>(() =>
    initialEvents.map((e, i) => toIdentifiedEvent(e, i)),
  );
  const feedEndRef = useRef<HTMLDivElement>(null);
  const [live, setLive] = useState(isLive);

  const handleNewEvent = useCallback(
    (event: AgentEvent) => {
      setEvents((prev) => [...prev, assignId(event)]);
      if (event.type === EVENT_TYPE.RUN_STARTED) setLive(true);
      if (event.type === EVENT_TYPE.RUN_COMPLETED) setLive(false);
    },
    [assignId],
  );

  const initialMaxSeq = useMemo(
    () => Math.max(0, ...initialEvents.map((e) => e.sequence ?? 0)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  useEventStream(sessionId, handleNewEvent, true, initialMaxSeq);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const runs = useMemo(() => groupEventsIntoRuns(events), [events]);

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
    <MotionConfig reducedMotion={reducedMotion ? "always" : "never"}>
      <div className="space-y-2">
        <AnimatePresence mode="sync">
          {runs.map((run) => {
            const runCompleted = run.events.some((e) => e.type === EVENT_TYPE.RUN_COMPLETED);
            return (
              <motion.div
                key={run.runId}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                <RunGroup events={run.events} isLive={live && !runCompleted} />
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={feedEndRef} />
      </div>
    </MotionConfig>
  );
}
