import { listSessions } from "@/lib/actions/sessions";
import { LiveSessionList } from "@/components/sessions/LiveSessionList";

export default async function DashboardPage() {
  const sessions = await listSessions();

  return (
    <div className="pt-10 pb-16">
      <LiveSessionList initialSessions={sessions} />
    </div>
  );
}
