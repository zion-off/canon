"use client";

import { useRef } from "react";
import { AgentEventSchema } from "@/lib/schemas/sessions";
import type { AgentEvent } from "@/lib/schemas/sessions";
import { StreamUrlResponseSchema } from "@/lib/schemas/auth";
import { useEventSource } from "./useEventSource";

async function fetchStreamUrl(path: string): Promise<string | null> {
  const res = await fetch(path);
  if (!res.ok) return null;
  const body = StreamUrlResponseSchema.parse(await res.json());
  return body.backendUrl;
}

/**
 * SSE hook for per‑session agent event streams.
 *
 * Wraps ``useEventSource`` with session-specific URL construction and
 * replay-position tracking.  Connects via the edge route to obtain a
 * short-lived stream token, then opens EventSource directly to the backend.
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
      return fetchStreamUrl(`/api/stream/${sessionId}?after=${after}`);
    },
    (data) => {
      const event = AgentEventSchema.parse(data);
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
