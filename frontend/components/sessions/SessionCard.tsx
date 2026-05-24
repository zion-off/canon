"use client";

import Link from "next/link";
import type { SessionResponse } from "@/lib/schemas/sessions";

interface SessionCardProps {
  session: SessionResponse;
}

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return `${Math.floor(diff / 86_400_000)}d ago`;
}

function statusColor(status: string): string {
  switch (status) {
    case "active":
      return "bg-emerald-500";
    case "completed":
      return "bg-slate-500";
    default:
      return "bg-slate-600";
  }
}

function borderColor(status: string): string {
  return status === "active" ? "border-l-blue-500" : "border-l-slate-700";
}

export function SessionCard({ session }: SessionCardProps) {
  const truncatedSummary = session.summary
    ? session.summary.length > 100
      ? `${session.summary.slice(0, 100)}…`
      : session.summary
    : null;

  return (
    <Link href={`/sessions/${session.sessionId}`} className="block group">
      <div
        className={`rounded-lg border border-white/[0.08] border-l-2 ${borderColor(session.status)} bg-[#0f0f1a] px-5 py-4 transition-colors group-hover:bg-[#141428]`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block h-2 w-2 rounded-full ${statusColor(session.status)}`}
            />
            <span className="font-medium text-slate-200">
              {session.title}
            </span>
          </div>
          <span className="text-sm text-slate-400">
            {relativeTime(session.lastRunAt ?? session.updatedAt)}
          </span>
        </div>

        <div className="mt-2 flex items-center justify-between">
          {truncatedSummary ? (
            <p className="text-sm text-slate-400">{truncatedSummary}</p>
          ) : (
            <p className="text-sm italic text-slate-500">No summary</p>
          )}
          <span className="ml-4 shrink-0 rounded-full bg-white/[0.06] px-2.5 py-0.5 text-xs text-slate-400">
            {session.runCount} run{session.runCount !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </Link>
  );
}
