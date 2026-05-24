"use client";

import { useEffect, useRef, useCallback } from "react";
import type { AgentEvent } from "@/lib/schemas/sessions";

export function useEventStream(
  sessionId: string,
  onEvent: (event: AgentEvent) => void,
  enabled: boolean,
) {
  const onEventRef = useRef(onEvent);
  const lastSequenceRef = useRef<number>(0);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const connect = useCallback(() => {
    if (!enabled) return undefined;

    const url = `/api/stream/${sessionId}?after=${lastSequenceRef.current}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (msg) => {
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

    eventSource.onerror = () => {
      eventSource.close();
      setTimeout(() => {
        connect();
      }, 2000);
    };

    return eventSource;
  }, [sessionId, enabled]);

  useEffect(() => {
    const eventSource = connect();
    return () => {
      eventSource?.close();
    };
  }, [connect]);
}
