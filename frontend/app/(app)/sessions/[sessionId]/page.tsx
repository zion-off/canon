import Link from "next/link";
import { getSession, getSessionEvents } from "@/lib/actions/sessions";
import { EventFeed } from "@/components/sessions/EventFeed";
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

export default async function SessionDetailPage({
  params,
}: SessionDetailPageProps) {
  const { sessionId } = await params;
  const [session, events] = await Promise.all([
    getSession(sessionId),
    getSessionEvents(sessionId),
  ]);

  const isLive = isSessionLive(events);

  return (
    <div className="space-y-6">
      <Link
        href={ROUTE_DASHBOARD}
        className="inline-flex items-center gap-1 text-sm text-canon-text-dim transition-colors hover:text-canon-text"
      >
        ← Sessions
      </Link>

      <header>
        <h1 className="font-syne text-2xl font-bold text-canon-text">
          {session.title}
        </h1>
        {session.summary && (
          <p className="mt-1 text-sm text-canon-text-dim">{session.summary}</p>
        )}
      </header>

      <EventFeed
        sessionId={sessionId}
        initialEvents={events}
        isLive={isLive}
      />
    </div>
  );
}
