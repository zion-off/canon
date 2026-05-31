"use client";

import { motion } from "motion/react";

interface ThoughtCardProps {
  message: string;
  index: number;
}

export function ThoughtCard({ message, index }: ThoughtCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="py-3 pl-4 border-l-2 border-canon-border"
    >
      <p className="text-[15px] leading-relaxed text-canon-text whitespace-pre-wrap">{message}</p>
    </motion.div>
  );
}
