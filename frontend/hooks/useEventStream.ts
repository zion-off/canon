"use client";

import { useEffect, useRef } from "react";
import type { AgentEvent } from "@/lib/schemas/sessions";

export function useEventStream(
  sessionId: string,
  onEvent: (event: AgentEvent) => void,
  enabled: boolean,
) {
  const onEventRef = useRef(onEvent);
  const lastSequenceRef = useRef<number>(0);
  const sourceRef = useRef<EventSource | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    unmountedRef.current = false;

    function connect() {
      if (!enabled || unmountedRef.current) return;

      const url = `/api/stream/${sessionId}?after=${lastSequenceRef.current}`;
      const es = new EventSource(url);
      sourceRef.current = es;

      es.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data) as AgentEvent;
          if (event.sequence !== null && event.sequence > lastSequenceRef.current) {
            lastSequenceRef.current = event.sequence;
          }
          onEventRef.current(event);
        } catch {
          // Ignore malformed messages
        }
      };

      es.onerror = () => {
        es.close();
        if (unmountedRef.current) return;
        timerRef.current = setTimeout(connect, 2000);
      };
    }

    connect();

    return () => {
      unmountedRef.current = true;
      sourceRef.current?.close();
      sourceRef.current = null;
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [sessionId, enabled]);
}
