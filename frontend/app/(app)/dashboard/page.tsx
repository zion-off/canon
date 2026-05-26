import { listSessions } from "@/lib/actions/sessions";
import { SessionRow } from "@/components/sessions/SessionRow";

const colHeader =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary";

export default async function DashboardPage() {
  const sessions = await listSessions();

  return (
    <div className="pt-10 pb-16">
      <div className="h-10 flex items-center border-b border-canon-border -mx-5 px-5 mb-0">
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
          <div className="grid grid-cols-[1fr_auto_auto] gap-x-6 px-5 py-2 border-b border-canon-border">
            <span className={colHeader}>Session</span>
            <span className={colHeader}>Status</span>
            <span className={`${colHeader} text-right`}>Last run</span>
          </div>
          {sessions.map((session) => (
            <SessionRow key={session.sessionId} session={session} />
          ))}
        </div>
      )}
    </div>
  );
}
