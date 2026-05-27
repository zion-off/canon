import type { ToolCallPair } from "@/lib/schemas/sessions";
import { HighlightedCode } from "../HighlightedCode";
import { formatTimestamp } from "@/lib/date-utils";
import { TOOL_DISPLAY_NAMES, AGENT_DISPLAY_NAMES, STATUS_DISPLAY } from "@/lib/constants";

interface ToolCallContentProps {
  pair: ToolCallPair;
  hideStatus?: boolean;
}

export function ToolCallContent({ pair, hideStatus = false }: ToolCallContentProps) {
  const { started, completed } = pair;
  const toolName = TOOL_DISPLAY_NAMES[started.payload.tool_name] ?? started.payload.tool_name;
  const authorName = started.author
    ? (AGENT_DISPLAY_NAMES[started.author] ?? started.author)
    : null;
  const isPending = completed === null;
  const isSuccess = completed?.payload.status === "ok";

  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="text-sm font-medium text-canon-text">{toolName}</span>
          {authorName && (
            <span className="text-xs text-canon-text-disabled font-condensed">{authorName}</span>
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
      {!hideStatus && (
        <>
          <div
            className={`mt-2 flex items-baseline justify-between gap-4 ${isPending ? "items-center" : ""}`}
          >
            <span
              className={`text-xs font-condensed font-bold uppercase tracking-wider ${
                isPending
                  ? "text-canon-warning italic normal-case"
                  : isSuccess
                    ? "text-canon-success"
                    : "text-canon-error"
              }`}
            >
              {isPending
                ? "running…"
                : (STATUS_DISPLAY[completed.payload.status] ?? completed.payload.status)}
            </span>
            {completed?.timestamp && (
              <span suppressHydrationWarning className="shrink-0 text-xs text-canon-text-disabled">
                {formatTimestamp(completed.timestamp)}
              </span>
            )}
          </div>
          {completed?.payload.result != null && (
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
  );
}
