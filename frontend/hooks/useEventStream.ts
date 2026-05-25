"use client";

import { useEffect, useRef } from "react";
import type { AgentEvent } from "@/lib/schemas/sessions";

const MAX_RETRIES = 10;
const BASE_DELAY = 1000;
const MAX_DELAY = 30_000;

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
  const retryCountRef = useRef(0);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    unmountedRef.current = false;
    retryCountRef.current = 0;

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

        retryCountRef.current += 1;
        if (retryCountRef.current > MAX_RETRIES) return;

        const delay = Math.min(BASE_DELAY * Math.pow(2, retryCountRef.current - 1), MAX_DELAY);
        timerRef.current = setTimeout(connect, delay);
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
