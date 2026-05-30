"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";

interface IntentHeaderProps {
  request: string;
  context: string;
  isLive: boolean;
}

export function IntentHeader({ request, context, isLive }: IntentHeaderProps) {
  const [showContext, setShowContext] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="rounded-md border border-canon-border bg-canon-surface p-5"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent">
            Intent
          </span>
          <p className="mt-1.5 text-base leading-relaxed text-canon-text">{request}</p>
        </div>
        {isLive && (
          <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
            <span className="inline-block h-2 w-2 rounded-full bg-canon-success animate-pulse" />
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-success">
              Live
            </span>
          </div>
        )}
      </div>

      {context && (
        <div className="mt-3">
          <button
            onClick={() => setShowContext(!showContext)}
            className="font-condensed text-xs text-canon-text-secondary hover:text-canon-text transition-colors"
          >
            {showContext ? "Hide context ▾" : "Show context ▸"}
          </button>
          <AnimatePresence>
            {showContext && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <pre className="mt-2 whitespace-pre-wrap text-xs text-canon-text-secondary font-mono leading-relaxed">
                  {context}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {isLive && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-3 text-xs text-canon-text-secondary italic"
        >
          Canon is consulting organizational memory…
        </motion.p>
      )}
    </motion.div>
  );
}
