"use client";

import Link from "next/link";
import type { SessionResponse } from "@/lib/schemas/sessions";
import { formatRelativeTime } from "@/lib/date-utils";
import { routeToSession, STATUS } from "@/lib/constants";

interface SessionRowProps {
  session: SessionResponse;
}

const labelClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em]";

function statusBadge(status: string) {
  switch (status) {
    case STATUS.ACTIVE:
      return { bg: "bg-canon-success-bg", text: "text-canon-success-fg", label: "Active" };
    case STATUS.COMPLETED:
      return { bg: "bg-canon-info-bg", text: "text-canon-info-fg", label: "Done" };
    default:
      return { bg: "bg-canon-border", text: "text-canon-text-secondary", label: status };
  }
}

export function SessionRow({ session }: SessionRowProps) {
  const badge = statusBadge(session.status);

  return (
    <Link
      href={routeToSession(session.sessionId)}
      className="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-5 py-3 border-b border-canon-border hover:bg-white/[0.05] transition-colors group"
    >
      <div className="min-w-0">
        <div className="font-condensed font-bold text-[2.5rem] leading-none text-canon-text truncate group-hover:text-canon-accent transition-colors">
          {session.title}
        </div>
        {session.summary && (
          <div className="mt-1 text-[0.75rem] text-canon-text-secondary truncate">
            {session.summary}
          </div>
        )}
      </div>

      <div className={`shrink-0 h-5 px-2 flex items-center ${badge.bg}`}>
        <span className={`${labelClass} ${badge.text}`}>{badge.label}</span>
      </div>

      <div
        className={`${labelClass} text-canon-text-secondary text-right shrink-0 tabular-nums`}
        suppressHydrationWarning
      >
        {formatRelativeTime(session.lastRunAt ?? session.updatedAt)}
      </div>
    </Link>
  );
}
