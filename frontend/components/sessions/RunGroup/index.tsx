"use client";

import type { IdentifiedEvent } from "@/lib/schemas/sessions";
import { HighlightedCode } from "../HighlightedCode";
import { MarkdownRenderer } from "../MarkdownRenderer";
import { SubagentGroupItem } from "../SubagentGroupItem";
import { formatDateTime, formatTimestamp } from "@/lib/date-utils";
import { EVENT_TYPE, DISPLAY_KIND, TOOL_NAME, STATUS_DISPLAY } from "@/lib/constants";
import type { TimelineSlotItem } from "./types";
import { pairToolCallEvents } from "./pairToolCallEvents";
import { TimelineSlot } from "./TimelineSlot";
import { ToolCallContent } from "./ToolCallContent";

interface RunGroupProps {
  runIndex: number;
  events: IdentifiedEvent[];
  timestamp: string | null;
  invocationArgs: { request: string; context: string } | null;
}

export function RunGroup({ runIndex, events, timestamp, invocationArgs }: RunGroupProps) {
  const visibleEvents = events.filter(
    (e) => e.type !== EVENT_TYPE.RUN_STARTED && e.type !== EVENT_TYPE.RUN_COMPLETED,
  );
  const displayItems = pairToolCallEvents(visibleEvents);
  const isRunActive = !events.some((e) => e.type === EVENT_TYPE.RUN_COMPLETED);

  // canonize_node pairs expand into two timeline slots: invocation + completion.
  // Other display items pass through as-is.
  const timelineSlots: TimelineSlotItem[] = displayItems.flatMap((item): TimelineSlotItem[] => {
    if (
      item.kind === DISPLAY_KIND.TOOL_CALL_PAIR &&
      item.started.payload.tool_name === TOOL_NAME.CANONIZE_NODE &&
      item.completed !== null
    ) {
      return [
        { variant: "canonize-invocation", pair: item },
        { variant: "canonize-completion", pair: item },
      ];
    }
    return [{ variant: "display-item", item }];
  });

  const harnessOffset = invocationArgs != null ? 1 : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 pb-1 pt-4">
        <span className="text-sm font-medium text-canon-text">Run {runIndex}</span>
        {timestamp && (
          <>
            <span className="text-canon-text-secondary">·</span>
            <span suppressHydrationWarning className="text-xs text-canon-text-secondary">
              {formatDateTime(timestamp)}
            </span>
          </>
        )}
      </div>

      <div>
        {invocationArgs && (
          <TimelineSlot
            dot="bg-canon-accent"
            dotPt="pt-1"
            isLast={timelineSlots.length === 0}
            lineActive={isRunActive}
          >
            <div className="leading-4">
              <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
                Harness Request
              </span>
              <HighlightedCode
                code={JSON.stringify(invocationArgs, null, 2)}
                lang="json"
                className="mt-1 text-xs"
              />
            </div>
          </TimelineSlot>
        )}

        {timelineSlots.map((slot, i) => {
          const isLast = harnessOffset + i === harnessOffset + timelineSlots.length - 1;

          if (slot.variant === "canonize-completion") {
            const isSuccess = slot.pair.completed?.payload.status === "ok";
            const dot = isSuccess ? "bg-canon-success" : "bg-canon-error";
            return (
              <TimelineSlot
                key={`${slot.pair.stableId}-done`}
                dot={dot}
                dotPt="pt-1"
                isLast={isLast}
                lineActive={false}
              >
                <div className="flex items-baseline justify-between gap-4">
                  <span className="text-xs font-condensed font-bold uppercase tracking-wider text-canon-success">
                    {STATUS_DISPLAY[slot.pair.completed?.payload.status ?? ""] ??
                      slot.pair.completed?.payload.status}
                  </span>
                  {slot.pair.completed?.timestamp && (
                    <span
                      suppressHydrationWarning
                      className="shrink-0 text-xs text-canon-text-disabled"
                    >
                      {formatTimestamp(slot.pair.completed.timestamp)}
                    </span>
                  )}
                </div>
                {slot.pair.completed?.payload.result != null && (
                  <HighlightedCode
                    code={
                      typeof slot.pair.completed.payload.result === "string"
                        ? slot.pair.completed.payload.result
                        : JSON.stringify(slot.pair.completed.payload.result, null, 2)
                    }
                    lang={typeof slot.pair.completed.payload.result === "string" ? "txt" : "json"}
                    className="mt-1 text-xs"
                  />
                )}
              </TimelineSlot>
            );
          }

          if (slot.variant === "canonize-invocation") {
            const isSuccess = slot.pair.completed?.payload.status === "ok";
            const dot = isSuccess ? "bg-canon-success" : "bg-canon-error";
            return (
              <TimelineSlot key={slot.pair.stableId} dot={dot} isLast={isLast} lineActive={false}>
                <ToolCallContent pair={slot.pair} hideStatus />
              </TimelineSlot>
            );
          }

          const item = slot.item;

          if (item.kind === DISPLAY_KIND.TOOL_CALL_PAIR) {
            const isPending = item.completed === null;
            const isSuccess = item.completed?.payload.status === "ok";
            const dot = isPending
              ? "bg-canon-warning"
              : isSuccess
                ? "bg-canon-success"
                : "bg-canon-error";
            return (
              <TimelineSlot
                key={item.stableId}
                dot={dot}
                dotPulse={isPending}
                isLast={isLast}
                lineActive={isRunActive && isPending}
              >
                <ToolCallContent pair={item} />
              </TimelineSlot>
            );
          }

          if (item.kind === DISPLAY_KIND.SUBAGENT_GROUP) {
            const hasActivePairs = item.toolPairs.some((p) => p.completed === null);
            return (
              <TimelineSlot
                key={item.stableId}
                dot="bg-canon-text-secondary"
                dotPt="pt-1"
                isLast={isLast}
                lineActive={isRunActive && !hasActivePairs}
              >
                <SubagentGroupItem group={item} />
              </TimelineSlot>
            );
          }

          if (item.type === EVENT_TYPE.REASONING_CHECKPOINT) {
            return (
              <TimelineSlot
                key={item.stableId}
                dot="bg-canon-accent"
                isLast={isLast}
                lineActive={isRunActive}
              >
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-canon-text">
                  {item.payload.message}
                </p>
              </TimelineSlot>
            );
          }

          if (item.type === EVENT_TYPE.FINAL_RESPONSE) {
            return (
              <TimelineSlot
                key={item.stableId}
                dot="bg-canon-accent"
                dotPt="pt-1"
                isLast={isLast}
                lineActive={isRunActive}
              >
                <div>
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="text-sm font-medium text-canon-text">Final Response</span>
                    {item.timestamp && (
                      <span
                        suppressHydrationWarning
                        className="shrink-0 text-xs text-canon-text-disabled"
                      >
                        {formatTimestamp(item.timestamp)}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 px-1">
                    <MarkdownRenderer>{item.payload.text}</MarkdownRenderer>
                  </div>
                </div>
              </TimelineSlot>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
}
