"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import type { SubagentGroup } from "@/lib/schemas/sessions";
import { AGENT_DISPLAY_NAMES } from "@/lib/constants";
import { ToolCallSentenceCard } from "./ToolCallSentenceCard";

// Applied to the w-px spine div inside the subagent group when active
const SHIMMER_SPINE =
  "bg-[linear-gradient(to_bottom,_rgb(48,48,48)_0%,_rgb(48,48,48)_25%,_rgba(255,255,255,0.6)_50%,_rgb(48,48,48)_75%,_rgb(48,48,48)_100%)] bg-[length:100%_200%] [animation:shimmer_1.5s_linear_infinite]";
const STATIC_SPINE = "bg-canon-border";

interface SubagentGroupCardProps {
  group: SubagentGroup;
  index: number;
  isActive: boolean;
}

export function SubagentGroupCard({ group, index, isActive }: SubagentGroupCardProps) {
  const [expanded, setExpanded] = useState(true);
  const displayName = AGENT_DISPLAY_NAMES[group.agentName] ?? group.agentName;
  const allDone = group.toolPairs.every((p) => p.completed !== null);
  const hasError = group.toolPairs.some((p) => p.completed?.payload.status === "error");
  const totalItems = group.toolPairs.length + group.checkpoints.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.04 }}
      className="py-1"
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left group"
      >
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full shrink-0 ${
            isActive || (!allDone && !hasError)
              ? "bg-canon-warning animate-pulse"
              : hasError
                ? "bg-canon-error"
                : "bg-canon-success"
          }`}
        />
        <span className="text-sm font-medium text-canon-text group-hover:text-canon-accent transition-colors">
          {displayName}
        </span>
        {totalItems > 0 && (
          <span className="text-xs text-canon-text-disabled font-mono">
            {group.toolPairs.length} call{group.toolPairs.length !== 1 ? "s" : ""}
            {group.checkpoints.length > 0
              ? ` · ${group.checkpoints.length} thought${group.checkpoints.length !== 1 ? "s" : ""}`
              : ""}
          </span>
        )}
        <span className="text-xs text-canon-text-disabled ml-auto">{expanded ? "▾" : "▸"}</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {/* Spine + content using w-px div, same technique as original TimelineSlot */}
            <div className="mt-1 flex gap-3">
              <div
                className={`w-0.5 self-stretch min-h-3 ${isActive ? SHIMMER_SPINE : STATIC_SPINE}`}
              />
              <div className="flex-1 min-w-0 space-y-0.5 pb-1">
                {[
                  ...group.checkpoints.map((c) => ({
                    type: "checkpoint" as const,
                    stableId: c.stableId,
                    data: c,
                  })),
                  ...group.toolPairs.map((p) => ({
                    type: "pair" as const,
                    stableId: p.stableId,
                    data: p,
                  })),
                ]
                  .sort((a, b) => a.stableId - b.stableId)
                  .map((item, i) => {
                    if (item.type === "checkpoint") {
                      return (
                        <p
                          key={item.stableId}
                          className="text-xs text-canon-text-secondary leading-relaxed py-1 whitespace-pre-wrap"
                        >
                          {item.data.payload.message}
                        </p>
                      );
                    }
                    return <ToolCallSentenceCard key={item.stableId} pair={item.data} index={i} />;
                  })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
