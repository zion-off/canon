"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import type { ToolCallPair } from "@/lib/schemas/sessions";
import { HighlightedCode } from "../HighlightedCode";
import { toolCallSentence, computeLatencyMs, formatLatency } from "./phase-utils";
import { MemoryChips } from "./MemoryChips";
import { TOOL_NAME, TOOL_CALL_STATUS } from "@/lib/constants";

interface ToolCallSentenceCardProps {
  pair: ToolCallPair;
  index: number;
}

export function ToolCallSentenceCard({ pair, index }: ToolCallSentenceCardProps) {
  const [showDetails, setShowDetails] = useState(false);
  const isPending = pair.completed === null;
  const isSuccess = pair.completed?.payload.status === TOOL_CALL_STATUS.OK;
  const isError = pair.completed?.payload.status === TOOL_CALL_STATUS.ERROR;
  const latencyMs = computeLatencyMs(pair);
  const sentence = toolCallSentence(pair);

  const isHybridSearch = pair.started.payload.tool_name === TOOL_NAME.HYBRID_SEARCH;
  const searchResults: Record<string, unknown>[] | null =
    isHybridSearch && pair.completed?.payload.result
      ? ((pair.completed.payload.result as { results?: Record<string, unknown>[] })?.results ?? null)
      : null;
  const hasSearchResults = searchResults !== null && searchResults.length > 0;

  const errorMessage: string | null = (() => {
    if (!isError || pair.completed?.payload.result == null) return null;
    const r = pair.completed.payload.result;
    if (typeof r === "string") return r;
    if (typeof r === "object" && r !== null && "error" in (r as object)) {
      return String((r as Record<string, unknown>).error);
    }
    return "Error";
  })();

  const resultForDisplay: string | null = (() => {
    if (pair.completed?.payload.result == null) return null;
    const r = pair.completed.payload.result;
    if (typeof r === "string") return r;
    return JSON.stringify(r, null, 2);
  })();

  const resultLang = typeof pair.completed?.payload.result === "string" ? "txt" : "json";

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.04 }}
      className="py-2"
    >
      <div className="flex items-center gap-2">
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full shrink-0 ${
            isPending
              ? "bg-canon-warning animate-pulse"
              : isSuccess
                ? "bg-canon-success"
                : "bg-canon-error"
          }`}
        />
        <span className="text-sm text-canon-text">{sentence}</span>
        {latencyMs !== null && (
          <span className="text-xs text-canon-text-disabled font-mono shrink-0">
            {formatLatency(latencyMs)}
          </span>
        )}
        {isPending && <span className="text-xs text-canon-warning italic">running…</span>}
      </div>

      {hasSearchResults ? (
        <div className="mt-2 ml-3.5">
          <MemoryChips results={searchResults!} />
        </div>
      ) : null}

      {errorMessage !== null ? (
        <div className="mt-1.5 ml-3.5">
          <span className="text-xs text-canon-error">{errorMessage}</span>
        </div>
      ) : null}

      <div className="ml-3.5 mt-1">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-xs text-canon-text-disabled hover:text-canon-text-secondary transition-colors font-mono"
        >
          {showDetails ? "Hide details ▾" : "Details ▸"}
        </button>
        <AnimatePresence>
          {showDetails && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <div className="mt-1.5 space-y-2">
                <div>
                  <span className="text-xs text-canon-text-disabled font-condensed uppercase">Args</span>
                  <HighlightedCode
                    code={JSON.stringify(pair.started.payload.args, null, 2)}
                    lang="json"
                    className="mt-0.5 text-xs"
                  />
                </div>
                {resultForDisplay !== null ? (
                  <div>
                    <span className="text-xs text-canon-text-disabled font-condensed uppercase">Result</span>
                    <HighlightedCode
                      code={resultForDisplay}
                      lang={resultLang}
                      className="mt-0.5 text-xs"
                    />
                  </div>
                ) : null}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
