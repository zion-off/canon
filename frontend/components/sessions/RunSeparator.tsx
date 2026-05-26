"use client";

interface RunSeparatorProps {
  label: string;
}

export function RunSeparator({ label }: RunSeparatorProps) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="h-px flex-1 bg-canon-border" />
      <span className="font-condensed font-bold text-xs uppercase tracking-[0.05em] text-canon-text-secondary">
        {label}
      </span>
      <div className="h-px flex-1 bg-canon-border" />
    </div>
  );
}
