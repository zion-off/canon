"use client";

import Link from "next/link";
import type { SessionResponse } from "@/lib/schemas/sessions";
import { formatRelativeTime } from "@/lib/date-utils";
import { routeToSession } from "@/lib/constants";

interface SessionRowProps {
  session: SessionResponse;
}

const labelClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em]";

export function SessionRow({ session }: SessionRowProps) {
  return (
    <Link
      href={routeToSession(session.sessionId)}
      className="grid grid-cols-[1fr_auto] gap-x-6 items-center px-5 py-3 border-b border-canon-border hover:bg-white/5 transition-colors group"
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

      <div
        className={`${labelClass} text-canon-text-secondary text-right shrink-0 tabular-nums`}
        suppressHydrationWarning
      >
        {formatRelativeTime(session.lastRunAt ?? session.updatedAt)}
      </div>
    </Link>
  );
}
