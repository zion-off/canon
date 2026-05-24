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
      return "bg-emerald-500";
    case STATUS.COMPLETED:
      return "bg-slate-500";
    default:
      return "bg-slate-600";
  }
}

function borderColor(status: string): string {
  return status === STATUS.ACTIVE ? "border-l-canon-blue" : "border-l-slate-700";
}

export function SessionCard({ session }: SessionCardProps) {
  const truncatedSummary = session.summary
    ? session.summary.length > 100
      ? `${session.summary.slice(0, 100)}…`
      : session.summary
    : null;

  return (
    <Link href={routeToSession(session.sessionId)} className="block group">
      <div
        className={`rounded-lg border border-canon-border border-l-2 ${borderColor(session.status)} bg-canon-surface px-5 py-4 transition-colors group-hover:bg-[#141428]`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`inline-block h-2 w-2 rounded-full ${statusColor(session.status)}`} />
            <span className="font-medium text-canon-text">{session.title}</span>
          </div>
          <span className="text-sm text-canon-text-dim">
            {formatRelativeTime(session.lastRunAt ?? session.updatedAt)}
          </span>
        </div>

        <div className="mt-2 flex items-center justify-between">
          {truncatedSummary ? (
            <p className="text-sm text-canon-text-dim">{truncatedSummary}</p>
          ) : (
            <p className="text-sm italic text-canon-muted">No summary</p>
          )}
          <span className="ml-4 shrink-0 rounded-full bg-white/[0.06] px-2.5 py-0.5 text-xs text-canon-text-dim">
            {session.runCount} run{session.runCount !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </Link>
  );
}
