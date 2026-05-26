import Link from "next/link";
import { ROUTE_DASHBOARD } from "@/lib/constants";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="space-y-6">
        <p className="font-condensed font-bold text-[8rem] leading-none text-canon-text-disabled">
          404
        </p>
        <p className="text-sm text-canon-text-secondary">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href={ROUTE_DASHBOARD}
          className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text hover:text-canon-text-secondary transition-colors"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
