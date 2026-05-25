"use client";

import { Button } from "@/components/ui/Button";
import { ROUTE_DASHBOARD } from "@/lib/constants";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canon-bg px-4">
      <div className="text-center max-w-md">
        <h1 className="font-syne text-2xl font-semibold text-canon-text mb-3">
          Something went wrong
        </h1>
        <p className="text-sm text-canon-text-dim mb-8">
          {error.message ||
            "An unexpected error occurred. Please try again or return to the dashboard."}
        </p>
        <details className="mb-8 text-left">
          <summary className="cursor-pointer text-xs text-canon-muted hover:text-canon-text-dim transition-colors">
            Error details
          </summary>
          <pre className="mt-2 whitespace-pre-wrap rounded-md bg-canon-bg/50 p-3 text-xs text-canon-muted font-mono">
            {error.name}: {error.message}
            {error.digest ? `\nDigest: ${error.digest}` : ""}
            {error.stack ? `\n\n${error.stack}` : ""}
          </pre>
        </details>
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
