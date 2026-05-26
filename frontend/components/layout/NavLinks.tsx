"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ROUTE_DASHBOARD, ROUTE_GRAPH, ROUTE_SETTINGS, ROLE_OWNER } from "@/lib/constants";

const navClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em] transition-colors";

const navItems = [
  { href: ROUTE_DASHBOARD, label: "Dashboard", exact: true },
  { href: ROUTE_GRAPH, label: "Graph", exact: false },
];

const adminItems = [{ href: ROUTE_SETTINGS, label: "Settings", exact: false }];

interface NavLinksProps {
  userRole: string | null;
}

export function NavLinks({ userRole }: NavLinksProps) {
  const pathname = usePathname();

  const allItems = [...navItems, ...(userRole === ROLE_OWNER ? adminItems : [])];

  return (
    <>
      {allItems.map((item) => {
        const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`${navClass} ${active ? "text-canon-text" : "text-canon-text-secondary hover:text-canon-text"}`}
          >
            {item.label}
          </Link>
        );
      })}
    </>
  );
}
