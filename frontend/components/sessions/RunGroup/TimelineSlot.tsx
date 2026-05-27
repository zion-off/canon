import React from "react";

export const SHIMMER_LINE =
  "bg-[linear-gradient(to_bottom,_rgb(48,48,48)_0%,_rgb(48,48,48)_25%,_rgba(255,255,255,0.6)_50%,_rgb(48,48,48)_75%,_rgb(48,48,48)_100%)] bg-[length:100%_200%] [animation:shimmer_1.5s_linear_infinite]";

interface TimelineSlotProps {
  dot: string;
  dotPt?: string;
  dotPulse?: boolean;
  isLast: boolean;
  lineActive: boolean;
  children: React.ReactNode;
}

export function TimelineSlot({
  dot,
  dotPt = "pt-1.5",
  dotPulse = false,
  isLast,
  lineActive,
  children,
}: TimelineSlotProps) {
  return (
    <div className="flex gap-3">
      <div className={`flex flex-col items-center ${dotPt}`}>
        <div
          className={`w-2 h-2 rounded-full shrink-0 ${dot}${dotPulse ? " animate-pulse" : ""}`}
        />
        {!isLast && (
          <div className={`w-px flex-1 mt-1 ${lineActive ? SHIMMER_LINE : "bg-canon-border"}`} />
        )}
      </div>
      <div className={`min-w-0 flex-1 ${isLast ? "pb-1" : "pb-4"}`}>{children}</div>
    </div>
  );
}
