"use client";

import type { DisplayItem } from "@/lib/schemas/sessions";
import { ToolCallTimeline } from "./ToolCallTimeline";
import { SubagentGroupItem } from "./SubagentGroupItem";
import { RunSeparator } from "./RunSeparator";
import { formatTimestamp } from "@/lib/date-utils";
import { isJsonContent } from "@/lib/text-utils";
import { EVENT_TYPE, DISPLAY_KIND } from "@/lib/constants";

interface EventItemProps {
  item: DisplayItem;
}

export function EventItem({ item }: EventItemProps) {
  if (item.kind === DISPLAY_KIND.TOOL_CALL_PAIR) {
    return <ToolCallTimeline pair={item} />;
  }

  if (item.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
    return <SubagentGroupItem group={item} />;
  }

  switch (item.type) {
    case EVENT_TYPE.RUN_STARTED:
      return <RunSeparator label="Run started" />;

    case EVENT_TYPE.RUN_COMPLETED:
      return <RunSeparator label="Run completed" />;

    case EVENT_TYPE.REASONING_CHECKPOINT:
      return (
        <div className="border-l-2 border-l-canon-accent bg-canon-surface px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
              Reasoning
            </span>
            {item.timestamp && (
              <span suppressHydrationWarning className="text-xs text-canon-text-secondary">
                {formatTimestamp(item.timestamp)}
              </span>
            )}
          </div>
          <p className="mt-2 whitespace-pre-wrap text-sm text-canon-text">{item.payload.message}</p>
        </div>
      );

    case EVENT_TYPE.FINAL_RESPONSE:
      return (
        <div className="flex gap-3">
          <div className="pt-1.5">
            <div className="w-2 h-2 rounded-full bg-canon-accent shrink-0" />
          </div>
          <div className="pb-1 min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-4">
              <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
                Final Response
              </span>
              {item.timestamp && (
                <span
                  suppressHydrationWarning
                  className="shrink-0 text-xs text-canon-text-disabled"
                >
                  {formatTimestamp(item.timestamp)}
                </span>
              )}
            </div>
            <div className="mt-1">
              {isJsonContent(item.payload.text) ? (
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-sm text-canon-text">
                  {item.payload.text}
                </pre>
              ) : (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-canon-text">
                  {item.payload.text}
                </p>
              )}
            </div>
          </div>
        </div>
      );

    default:
      return null;
  }
}
