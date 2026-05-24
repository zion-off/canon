"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { ROUTE_DASHBOARD } from "@/lib/constants";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-canon-bg px-4">
      <div className="text-center max-w-md">
        <h1 className="font-syne text-2xl font-semibold text-canon-text mb-3">
          Something went wrong
        </h1>
        <p className="text-sm text-canon-text-dim mb-8">
          An unexpected error occurred. Please try again or return to the dashboard.
        </p>
        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => reset()}>
            Try again
          </Button>
          <Button onClick={() => (window.location.href = ROUTE_DASHBOARD)}>Go to Dashboard</Button>
        </div>
      </div>
    </div>
  );
}
