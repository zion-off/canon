import Link from "next/link";
import { NavLinks } from "./NavLinks";
import { ROUTE_DASHBOARD } from "@/lib/constants";

const navClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em] transition-colors";

interface AppHeaderProps {
  userRole: string | null;
}

export function AppHeader({ userRole }: AppHeaderProps) {
  return (
    <header className="shrink-0 bg-canon-bg z-50 sticky top-0">
      <div className="h-10 flex items-center justify-between px-5 border-b border-canon-border">
        <Link
          href={ROUTE_DASHBOARD}
          className="font-condensed font-bold text-sm uppercase tracking-wide text-canon-text hover:text-canon-text-secondary transition-colors"
        >
          canon
        </Link>

        <nav className="flex items-center gap-6">
          <NavLinks userRole={userRole} />

          <form method="post" action="/api/logout" className="inline-flex items-center">
            <button
              type="submit"
              className={`${navClass} text-canon-text-secondary hover:text-canon-error cursor-pointer`}
            >
              Logout
            </button>
          </form>
        </nav>
      </div>
    </header>
  );
}
