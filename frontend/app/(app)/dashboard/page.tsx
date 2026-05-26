import { listSessions, listMySessions } from "@/lib/actions/sessions";
import { getCurrentUser } from "@/lib/actions/auth";
import { LiveSessionList } from "@/components/sessions/LiveSessionList";

export default async function DashboardPage() {
  const user = await getCurrentUser();
  const [mySessions, teamSessions] = await Promise.all([listMySessions(), listSessions()]);

  return (
    <div className="pt-10 pb-16">
      <LiveSessionList
        mySessions={mySessions}
        teamSessions={teamSessions}
        currentUserId={user?.userId ?? ""}
      />
    </div>
  );
}
