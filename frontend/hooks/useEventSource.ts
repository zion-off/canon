"use client";

import { useEffect, useRef } from "react";

const MAX_RETRIES = 10;
const BASE_DELAY = 1_000;
const MAX_DELAY = 30_000;

/**
 * Generic EventSource hook with exponential‑backoff reconnect.
 *
 * `buildUrl` is called on every connect (initial + reconnect) so wrappers can
 * inject dynamic state like replay position.  Only `enabled` triggers
 * disconnect/reconnect — `buildUrl` identity changes are ignored.
 *
 * `onMessage` receives parsed JSON and is kept stable via ref.
 */
export function useEventSource(
  buildUrl: () => string | null,
  onMessage: (data: unknown) => void,
  enabled: boolean,
) {
  const buildUrlRef = useRef(buildUrl);
  const onMessageRef = useRef(onMessage);

  // Sync latest callbacks without reconnecting.
  useEffect(() => {
    buildUrlRef.current = buildUrl;
    onMessageRef.current = onMessage;
  });

  // Only `enabled` triggers disconnect/reconnect.
  useEffect(() => {
    if (!enabled) return;

    let source: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let unmounted = false;
    let retryCount = 0;

    function connect() {
      if (unmounted) return;

      const url = buildUrlRef.current();
      if (url === null) return;

      source = new EventSource(url);

      source.onmessage = (msg) => {
        try {
          onMessageRef.current(JSON.parse(msg.data));
          retryCount = 0;
        } catch {
          // Ignore malformed messages
        }
      };

      source.onerror = () => {
        source?.close();
        if (unmounted) return;

        retryCount += 1;
        if (retryCount > MAX_RETRIES) return;

        timer = setTimeout(connect, Math.min(BASE_DELAY * Math.pow(2, retryCount - 1), MAX_DELAY));
      };
    }

    connect();

    return () => {
      unmounted = true;
      source?.close();
      if (timer !== null) clearTimeout(timer);
    };
  }, [enabled]);
}
