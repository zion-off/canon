"use client";

interface RunSeparatorProps {
  label: string;
}

export function RunSeparator({ label }: RunSeparatorProps) {
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="h-px flex-1 bg-slate-700/50" />
      <span className="text-xs text-canon-muted">{label}</span>
      <div className="h-px flex-1 bg-slate-700/50" />
    </div>
  );
}
