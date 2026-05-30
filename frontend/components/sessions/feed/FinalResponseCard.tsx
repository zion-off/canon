"use client";

import { motion } from "motion/react";
import { MarkdownRenderer } from "../MarkdownRenderer";

interface FinalResponseCardProps {
  text: string;
  index: number;
}

export function FinalResponseCard({ text, index }: FinalResponseCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className="py-3"
    >
      <div className="border-l-2 border-canon-accent/50 pl-4">
        <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-accent mb-2 block">
          Verdict
        </span>
        <div className="prose-sm">
          <MarkdownRenderer>{text}</MarkdownRenderer>
        </div>
      </div>
    </motion.div>
  );
}
