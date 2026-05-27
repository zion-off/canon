"use client";

import type { ToolCallPair } from "@/lib/schemas/sessions";
import { HighlightedCode } from "./HighlightedCode";
import { AGENT_DISPLAY_NAMES, TOOL_DISPLAY_NAMES } from "@/lib/constants";
import { formatTimestamp } from "@/lib/date-utils";

const STATUS_DISPLAY: Record<string, string> = {
  ok: "Done",
  error: "Failed",
};

interface ToolCallTimelineProps {
  pair: ToolCallPair;
}

export function ToolCallTimeline({ pair }: ToolCallTimelineProps) {
  const { started, completed } = pair;
  const toolName = TOOL_DISPLAY_NAMES[started.payload.tool_name] ?? started.payload.tool_name;
  const authorName = started.author
    ? (AGENT_DISPLAY_NAMES[started.author] ?? started.author)
    : null;
  const isPending = completed === null;
  const isSuccess = completed?.payload.status === "ok";

  return (
    <div>
      {/* Started node */}
      <div className="flex gap-3">
        <div className="flex flex-col items-center pt-1.5">
          <div className="w-2 h-2 rounded-full bg-canon-accent shrink-0" />
          <div className="w-px flex-1 bg-canon-border mt-1" />
        </div>
        <div className="pb-3 min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-4">
            <div className="flex items-baseline gap-2 min-w-0">
              <span className="text-sm font-medium text-canon-text">{toolName}</span>
              {authorName && (
                <span className="text-xs text-canon-text-disabled font-condensed">
                  {authorName}
                </span>
              )}
            </div>
            {started.timestamp && (
              <span suppressHydrationWarning className="shrink-0 text-xs text-canon-text-disabled">
                {formatTimestamp(started.timestamp)}
              </span>
            )}
          </div>

          {Object.keys(started.payload.args).length > 0 && (
            <HighlightedCode
              code={JSON.stringify(started.payload.args, null, 2)}
              lang="json"
              className="mt-1 text-xs"
            />
          )}
        </div>
      </div>

      {/* Completed node */}
      <div className={`flex gap-3 ${isPending ? "items-center" : ""}`}>
        <div className={isPending ? undefined : "pt-1"}>
          <div
            className={`w-2 h-2 rounded-full shrink-0 ${
              isPending
                ? "bg-canon-warning animate-pulse"
                : isSuccess
                  ? "bg-canon-success"
                  : "bg-canon-error"
            }`}
          />
        </div>
        <div className="pb-1 min-w-0 flex-1">
          {isPending ? (
            <span className="text-xs text-canon-warning italic">running…</span>
          ) : (
            <>
              <div className="flex items-baseline justify-between gap-4">
                <span
                  className={`text-xs font-condensed font-bold uppercase tracking-wider ${
                    isSuccess ? "text-canon-success" : "text-canon-error"
                  }`}
                >
                  {STATUS_DISPLAY[completed.payload.status] ?? completed.payload.status}
                </span>
                {completed.timestamp && (
                  <span
                    suppressHydrationWarning
                    className="shrink-0 text-xs text-canon-text-disabled"
                  >
                    {formatTimestamp(completed.timestamp)}
                  </span>
                )}
              </div>
              {completed.payload.result != null && (
                <HighlightedCode
                  code={
                    typeof completed.payload.result === "string"
                      ? completed.payload.result
                      : JSON.stringify(completed.payload.result, null, 2)
                  }
                  lang={typeof completed.payload.result === "string" ? "txt" : "json"}
                  className="mt-1 text-xs"
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
