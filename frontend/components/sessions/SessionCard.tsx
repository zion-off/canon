"use client";

import Link from "next/link";
import type { SessionResponse } from "@/lib/schemas/sessions";
import { formatRelativeTime } from "@/lib/date-utils";
import { routeToSession } from "@/lib/constants";

interface SessionCardProps {
  session: SessionResponse;
}

export function SessionCard({ session }: SessionCardProps) {
  const truncatedSummary = session.summary
    ? session.summary.length > 120
      ? `${session.summary.slice(0, 120)}…`
      : session.summary
    : null;

  return (
    <Link href={routeToSession(session.sessionId)} className="block group">
      <div className="border border-canon-border bg-canon-surface px-5 py-4 transition-colors group-hover:bg-white/5">
        <div className="flex items-center justify-between gap-4">
          <span className="font-medium text-canon-text truncate">{session.title}</span>
          <div className="flex items-center gap-3 shrink-0">
            <span className="bg-canon-surface-raised px-2 font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
              {session.runCount} run{session.runCount !== 1 ? "s" : ""}
            </span>
            <span className="text-xs text-canon-text-secondary" suppressHydrationWarning>
              {formatRelativeTime(session.lastRunAt ?? session.updatedAt)}
            </span>
          </div>
        </div>

        {(truncatedSummary || !session.summary) && (
          <div className="mt-2 pl-3.5">
            {truncatedSummary ? (
              <p className="text-sm text-canon-text-secondary">{truncatedSummary}</p>
            ) : (
              <p className="text-sm italic text-canon-text-secondary">No summary</p>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
