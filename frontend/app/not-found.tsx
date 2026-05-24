import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ROUTE_DASHBOARD } from "@/lib/constants";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canon-bg px-4">
      <div className="text-center max-w-md">
        <h1 className="font-syne text-6xl font-bold text-canon-text-dim mb-4">
          404
        </h1>
        <p className="text-sm text-canon-text-dim mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link href={ROUTE_DASHBOARD}>
          <Button>Go to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}