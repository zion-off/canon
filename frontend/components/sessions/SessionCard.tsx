"use client";

import Link from "next/link";
import type { SessionResponse } from "@/lib/schemas/sessions";
import { formatRelativeTime } from "@/lib/date-utils";
import { routeToSession, STATUS } from "@/lib/constants";

interface SessionCardProps {
  session: SessionResponse;
}

function statusColor(status: string): string {
  switch (status) {
    case STATUS.ACTIVE:
      return "bg-canon-success";
    case STATUS.COMPLETED:
      return "bg-canon-text-secondary";
    default:
      return "bg-canon-border";
  }
}

function activeBorder(status: string): string {
  return status === STATUS.ACTIVE ? "border-l-canon-accent" : "border-l-canon-border";
}

export function SessionCard({ session }: SessionCardProps) {
  const truncatedSummary = session.summary
    ? session.summary.length > 120
      ? `${session.summary.slice(0, 120)}…`
      : session.summary
    : null;

  return (
    <Link href={routeToSession(session.sessionId)} className="block group">
      <div
        className={`border border-canon-border border-l-2 ${activeBorder(session.status)} bg-canon-surface px-5 py-4 transition-colors group-hover:bg-white/[0.05]`}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`shrink-0 inline-block h-1.5 w-1.5 ${statusColor(session.status)}`} />
            <span className="font-medium text-canon-text truncate">{session.title}</span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="bg-canon-surface-raised px-2 font-condensed font-bold text-xs uppercase tracking-[0.05em] text-canon-text-secondary">
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
