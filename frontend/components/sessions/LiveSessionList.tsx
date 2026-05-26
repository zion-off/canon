"use client";

import { useState, useCallback } from "react";
import type { SessionResponse } from "@/lib/schemas/sessions";
import { SessionResponseSchema } from "@/lib/schemas/sessions";
import { useEventSource } from "@/hooks/useEventSource";
import { SessionRow } from "./SessionRow";

const colHeader =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary";

interface LiveSessionListProps {
  initialSessions: SessionResponse[];
}

export function LiveSessionList({ initialSessions }: LiveSessionListProps) {
  const [sessions, setSessions] = useState(initialSessions);

  const onSession = useCallback((data: unknown) => {
    const parsed = SessionResponseSchema.safeParse(data);
    if (!parsed.success) return;
    const incoming = parsed.data;
    setSessions((prev) => {
      const idx = prev.findIndex((s) => s.sessionId === incoming.sessionId);
      if (idx === -1) return [incoming, ...prev];
      const copy = [...prev];
      copy[idx] = incoming;
      return copy;
    });
  }, []);

  useEventSource(() => "/api/sessions/stream", onSession, true);

  return (
    <>
      <div className="h-10 flex items-center border-b border-canon-border -mx-5 px-5">
        <span className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text">
          Sessions
        </span>
        <span className="ml-3 font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary">
          {sessions.length} total
        </span>
      </div>

      {sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 border-b border-canon-border -mx-5 px-5">
          <p className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary">
            No sessions yet
          </p>
        </div>
      ) : (
        <div className="-mx-5">
          <div className="grid grid-cols-[1fr_auto] gap-x-6 px-5 py-2 border-b border-canon-border">
            <span className={colHeader}>Session</span>
            <span className={`${colHeader} text-right`}>Last run</span>
          </div>
          {sessions.map((session) => (
            <SessionRow key={session.sessionId} session={session} />
          ))}
        </div>
      )}
    </>
  );
}
