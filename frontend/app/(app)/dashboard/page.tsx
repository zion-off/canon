import { listSessions } from "@/lib/actions/sessions";
import { SessionCard } from "@/components/sessions/SessionCard";

export default async function DashboardPage() {
  const sessions = await listSessions();

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-syne text-3xl font-bold text-canon-text">
          Sessions
        </h1>
        <p className="mt-1 text-sm text-canon-text-dim">
          {sessions.length} session{sessions.length !== 1 ? "s" : ""} across
          your team
        </p>
      </header>

      {sessions.length === 0 ? (
        <div className="rounded-lg border border-canon-border bg-canon-surface px-6 py-12 text-center">
          <p className="text-canon-text-dim">
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
