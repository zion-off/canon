"use client";

import { useRef } from "react";
import type { AgentEvent } from "@/lib/schemas/sessions";
import { useEventSource } from "./useEventSource";

/**
 * SSE hook for per‑session agent event streams.
 *
 * Wraps `useEventSource` with session‑specific URL construction and replay‑position
 * tracking so callers only need to provide `sessionId`, a callback, and whether
 * to connect.
 */
export function useEventStream(
  sessionId: string,
  onEvent: (event: AgentEvent) => void,
  enabled: boolean,
  initialSequence?: number,
) {
  const lastSequenceRef = useRef<number | null>(initialSequence ?? null);

  useEventSource(
    () => {
      const after = lastSequenceRef.current ?? 0;
      return `/api/stream/${sessionId}?after=${after}`;
    },
    (data) => {
      const event = data as AgentEvent;
      if (
        event.sequence !== null &&
        (lastSequenceRef.current === null || event.sequence > lastSequenceRef.current)
      ) {
        lastSequenceRef.current = event.sequence;
      }
      onEvent(event);
    },
    enabled,
  );
}
