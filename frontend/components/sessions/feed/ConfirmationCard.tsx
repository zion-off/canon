"use client";

import { motion } from "motion/react";
import type { IdentifiedEvent, ConfirmationReceivedEvent } from "@/lib/schemas/sessions";
import { ConfirmationRequestedPayloadSchema } from "@/lib/schemas/sessions";

interface ConfirmationCardProps {
  event: IdentifiedEvent;
  resolution?: ConfirmationReceivedEvent;
  index: number;
}

export function ConfirmationCard({ event, resolution, index }: ConfirmationCardProps) {
  const parsed = ConfirmationRequestedPayloadSchema.safeParse(event.payload);
  const payload = parsed.success ? parsed.data : { confirmationId: undefined, title: undefined, description: undefined, message: undefined };
  const isResolved = !!resolution;
  const accepted = resolution?.payload.accepted;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className={`rounded-md border p-4 w-fit ${
        isResolved
          ? accepted
            ? "border-canon-success/40 bg-canon-success-bg/20"
            : "border-canon-error/40 bg-canon-error-bg/20"
          : "border-canon-warning/30 bg-canon-surface"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <span className="font-condensed font-bold text-xs uppercase tracking-wider text-canon-warning">
            Confirmation Required
          </span>
          {payload.title && <h4 className="mt-1 text-sm font-medium text-canon-text">{payload.title}</h4>}
          {(payload.description || payload.message) && (
            <p className="mt-1 text-sm text-canon-text-secondary leading-relaxed">
              {payload.description || payload.message}
            </p>
          )}
        </div>

        {isResolved && (
          <span
            className={`font-condensed font-bold text-xs uppercase tracking-wider shrink-0 ${
              accepted ? "text-canon-success" : "text-canon-error"
            }`}
          >
            {accepted ? "Confirmed" : "Declined"}
          </span>
        )}
      </div>

      {!isResolved && (
        <p className="mt-2 text-xs text-canon-text-disabled italic">
          Awaiting user confirmation on the harness…
        </p>
      )}
    </motion.div>
  );
}
