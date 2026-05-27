"use client";

import type { SubagentGroup } from "@/lib/schemas/sessions";
import { ToolCallTimeline } from "./ToolCallTimeline";
import { AGENT_DISPLAY_NAMES } from "@/lib/constants";
import { formatTimestamp } from "@/lib/date-utils";

interface SubagentGroupItemProps {
  group: SubagentGroup;
}

export function SubagentGroupItem({ group }: SubagentGroupItemProps) {
  const displayName = AGENT_DISPLAY_NAMES[group.agentName] ?? group.agentName;

  return (
    <div className="ml-3 pl-3 border-l border-canon-border">
      <div className="flex items-baseline justify-between gap-4 mb-2">
        <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
          {displayName}
        </span>
        {group.timestamp && (
          <span suppressHydrationWarning className="shrink-0 text-xs text-canon-text-disabled">
            {formatTimestamp(group.timestamp)}
          </span>
        )}
      </div>
      {group.toolPairs.length > 0 && (
        <div className="ml-3 pl-3 border-l border-canon-border space-y-2">
          {group.toolPairs.map((pair) => (
            <ToolCallTimeline key={pair.stableId} pair={pair} />
          ))}
        </div>
      )}
    </div>
  );
}
