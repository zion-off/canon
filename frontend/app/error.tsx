"use client";

import { ROUTE_DASHBOARD } from "@/lib/constants";

const actionClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] transition-colors cursor-pointer disabled:opacity-[0.38]";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div>
          <p className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary mb-2">
            Error
          </p>
          <p className="text-sm text-canon-text-secondary">
            {error.message ||
              "An unexpected error occurred. Please try again or return to the dashboard."}
          </p>
        </div>

        <details>
          <summary className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary hover:text-canon-text transition-colors cursor-pointer">
            Details
          </summary>
          <pre className="mt-3 border-b border-canon-border pb-3 overflow-x-auto font-mono text-xs text-canon-text-secondary">
            {error.name}: {error.message}
            {error.digest ? `\nDigest: ${error.digest}` : ""}
            {error.stack ? `\n\n${error.stack}` : ""}
          </pre>
        </details>

        <div className="flex gap-6">
          <button
            type="button"
            onClick={() => reset()}
            className={`${actionClass} text-canon-text hover:text-canon-text-secondary`}
          >
            Try again
          </button>
          <button
            type="button"
            onClick={() => (window.location.href = ROUTE_DASHBOARD)}
            className={`${actionClass} text-canon-text-secondary hover:text-canon-text`}
          >
            Go to dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
