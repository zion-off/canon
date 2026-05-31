export type BadgeVariant = string;

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const knownStyles: Record<string, string> = {
  active: "bg-canon-info-bg text-canon-info-fg",
  in_progress: "bg-canon-warning-bg text-canon-warning-fg",
  deprecated: "bg-canon-surface text-canon-text-secondary",
  resolved: "bg-canon-success-bg text-canon-success-fg",
  completed: "bg-canon-success-bg text-canon-success-fg",
};

const defaultStyle = "bg-canon-surface text-canon-text-secondary";

export function Badge({ variant, children, className = "" }: BadgeProps) {
  const style = variant ? (knownStyles[variant] ?? defaultStyle) : defaultStyle;
  return (
    <span
      className={`inline-flex items-center h-5 px-2 font-condensed font-bold text-xs uppercase tracking-[0.05em] ${style} ${className}`}
    >
      {children}
    </span>
  );
}
