import Link from "next/link";
import { getSession, getSessionEvents } from "@/lib/actions/sessions";
import { EventFeed } from "@/components/sessions/feed";
import { ROUTE_DASHBOARD, EVENT_TYPE } from "@/lib/constants";

interface SessionDetailPageProps {
  params: Promise<{ sessionId: string }>;
}

function isSessionLive(events: { type: string }[]): boolean {
  if (events.length === 0) return false;

  let lastRunStartedIndex = -1;
  let lastRunCompletedIndex = -1;

  for (let i = 0; i < events.length; i++) {
    if (events[i].type === EVENT_TYPE.RUN_STARTED) lastRunStartedIndex = i;
    if (events[i].type === EVENT_TYPE.RUN_COMPLETED) lastRunCompletedIndex = i;
  }

  return lastRunStartedIndex > lastRunCompletedIndex;
}

const labelClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em]";

export default async function SessionDetailPage({ params }: SessionDetailPageProps) {
  const { sessionId } = await params;
  const [session, events] = await Promise.all([getSession(sessionId), getSessionEvents(sessionId)]);

  const isLive = isSessionLive(events);

  return (
    <div>
      <div className="h-10 flex items-center gap-3 border-b border-canon-border -mx-5 px-5">
        <Link
          href={ROUTE_DASHBOARD}
          className={`${labelClass} text-canon-text-secondary hover:text-canon-text transition-colors`}
        >
          Sessions
        </Link>
        <span className={`${labelClass} text-canon-text-disabled`}>·</span>
        <span className={`${labelClass} text-canon-text truncate`}>{session.title}</span>
      </div>

      <div className="pt-8 pb-4">
        <h1 className="font-condensed font-bold text-[2.5rem] leading-none text-canon-text">
          {session.title}
        </h1>
        {session.summary && (
          <p className="mt-2 text-sm text-canon-text-secondary">{session.summary}</p>
        )}
      </div>

      <EventFeed sessionId={sessionId} initialEvents={events} isLive={isLive} />
    </div>
  );
}
