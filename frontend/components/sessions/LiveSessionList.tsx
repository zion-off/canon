"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import type { SessionResponse, SessionListResponse } from "@/lib/schemas/sessions";
import { SessionResponseSchema } from "@/lib/schemas/sessions";
import { StreamUrlResponseSchema } from "@/lib/schemas/auth";
import { useEventSource } from "@/hooks/useEventSource";
import { listSessions, listMySessions } from "@/lib/actions/sessions";
import { SessionRow } from "./SessionRow";

const colHeader =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary";

const tabBase =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] cursor-pointer pb-2 border-b-2 transition-colors";
const tabActive = "text-canon-text border-canon-text";
const tabInactive = "text-canon-text-secondary border-transparent hover:text-canon-text";

interface LiveSessionListProps {
  mySessions: SessionListResponse;
  teamSessions: SessionListResponse;
  currentUserId: string;
}

function mergeSessions(prev: SessionResponse[], incoming: SessionResponse): SessionResponse[] {
  const idx = prev.findIndex((s) => s.sessionId === incoming.sessionId);
  if (idx === -1) return [incoming, ...prev];
  const copy = [...prev];
  copy[idx] = incoming;
  return copy;
}

async function fetchSessionsStreamUrl(): Promise<string | null> {
  const res = await fetch("/api/sessions/stream");
  if (!res.ok) return null;
  const body = StreamUrlResponseSchema.parse(await res.json());
  return body.backendUrl;
}

export function LiveSessionList({ mySessions, teamSessions, currentUserId }: LiveSessionListProps) {
  const [activeTab, setActiveTab] = useState<"yours" | "team">("yours");

  const [myState, setMyState] = useState(mySessions.sessions);
  const [myTotal, setMyTotal] = useState(mySessions.total);
  const [myNextCursor, setMyNextCursor] = useState(mySessions.nextCursor);

  const [teamState, setTeamState] = useState(teamSessions.sessions);
  const [teamTotal, setTeamTotal] = useState(teamSessions.total);
  const [teamNextCursor, setTeamNextCursor] = useState(teamSessions.nextCursor);

  const [loading, setLoading] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const onSession = useCallback(
    (data: unknown) => {
      const parsed = SessionResponseSchema.safeParse(data);
      if (!parsed.success) return;
      const incoming = parsed.data;

      setTeamState((prev) => {
        const isNew = !prev.some((s) => s.sessionId === incoming.sessionId);
        if (isNew) setTeamTotal((t) => t + 1);
        return mergeSessions(prev, incoming);
      });
      if (incoming.userId === currentUserId) {
        setMyState((prev) => {
          const isNew = !prev.some((s) => s.sessionId === incoming.sessionId);
          if (isNew) setMyTotal((t) => t + 1);
          return mergeSessions(prev, incoming);
        });
      }
    },
    [currentUserId],
  );

  useEventSource(fetchSessionsStreamUrl, onSession, true);

  const loadMore = useCallback(async () => {
    if (loading) return;
    const cursor = activeTab === "yours" ? myNextCursor : teamNextCursor;
    if (!cursor) return;

    setLoading(true);
    try {
      if (activeTab === "yours") {
        const result = await listMySessions(cursor);
        setMyState((prev) => [...prev, ...result.sessions]);
        setMyNextCursor(result.nextCursor);
      } else {
        const result = await listSessions(cursor);
        setTeamState((prev) => [...prev, ...result.sessions]);
        setTeamNextCursor(result.nextCursor);
      }
    } finally {
      setLoading(false);
    }
  }, [activeTab, myNextCursor, teamNextCursor, loading]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) loadMore();
    });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore]);

  const sessions = activeTab === "yours" ? myState : teamState;
  const hasMore = activeTab === "yours" ? !!myNextCursor : !!teamNextCursor;

  return (
    <>
      <div className="flex items-center gap-4 border-b border-canon-border -mx-5 px-5 pt-3 sticky top-10 bg-canon-bg z-40">
        <button
          type="button"
          className={`${tabBase} ${activeTab === "yours" ? tabActive : tabInactive}`}
          onClick={() => setActiveTab("yours")}
        >
          Yours
          <span className="ml-1.5 text-canon-text-secondary">{myTotal}</span>
        </button>
        <button
          type="button"
          className={`${tabBase} ${activeTab === "team" ? tabActive : tabInactive}`}
          onClick={() => setActiveTab("team")}
        >
          Team
          <span className="ml-1.5 text-canon-text-secondary">{teamTotal}</span>
        </button>
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
          {hasMore && <div ref={sentinelRef} className="h-8" />}
          {loading && (
            <div className="py-4 flex justify-center">
              <span className="font-condensed text-xs uppercase tracking-[0.08em] text-canon-text-secondary">
                Loading...
              </span>
            </div>
          )}
        </div>
      )}
    </>
  );
}
