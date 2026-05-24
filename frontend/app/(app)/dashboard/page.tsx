import { listSessions } from "@/lib/actions/sessions";
import { SessionCard } from "@/components/sessions/SessionCard";

export default async function DashboardPage() {
  const sessions = await listSessions();

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-[family-name:var(--font-syne)] text-3xl font-bold text-slate-200">
          Sessions
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {sessions.length} session{sessions.length !== 1 ? "s" : ""} across
          your team
        </p>
      </header>

      {sessions.length === 0 ? (
        <div className="rounded-lg border border-white/[0.08] bg-[#0f0f1a] px-6 py-12 text-center">
          <p className="text-slate-400">
            No sessions yet. Start your coding harness to see Canon&apos;s
            activity here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <SessionCard key={session.sessionId} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}
