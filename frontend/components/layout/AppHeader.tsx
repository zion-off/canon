import Link from "next/link";
import { handleLogout } from "@/lib/actions/auth";
import { ROUTE_DASHBOARD, ROUTE_GRAPH, ROUTE_SETTINGS, ROLE_OWNER } from "@/lib/constants";

interface AppHeaderProps {
  user: {
    name: string;
    email: string;
    role: string | null;
  };
}

export function AppHeader({ user }: AppHeaderProps) {
  const initial = user.name.charAt(0).toUpperCase();

  return (
    <header className="sticky top-0 z-50 border-b border-canon-border bg-[rgba(8,8,16,0.85)] backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link
          href={ROUTE_DASHBOARD}
          className="font-syne text-lg font-bold tracking-tight text-canon-text hover:text-white transition-colors"
        >
          Canon
        </Link>

        <nav className="flex items-center gap-6">
          <Link
            href={ROUTE_DASHBOARD}
            className="text-sm text-canon-text-dim hover:text-canon-text transition-colors"
          >
            Dashboard
          </Link>
          <Link
            href={ROUTE_GRAPH}
            className="text-sm text-canon-text-dim hover:text-canon-text transition-colors"
          >
            Graph
          </Link>
          {user.role === ROLE_OWNER && (
            <Link
              href={ROUTE_SETTINGS}
              className="text-sm text-canon-text-dim hover:text-canon-text transition-colors"
            >
              Settings
            </Link>
          )}
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full bg-canon-surface-2 border border-canon-border text-sm font-medium text-canon-text"
            title={user.email}
          >
            {initial}
          </div>
          <form action={handleLogout}>
            <button
              type="submit"
              className="text-sm text-canon-text-dim hover:text-canon-text transition-colors cursor-pointer"
            >
              Logout
            </button>
          </form>
        </nav>
      </div>
    </header>
  );
}
