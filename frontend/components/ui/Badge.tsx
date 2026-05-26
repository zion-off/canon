export type BadgeVariant =
  | "active"
  | "in_progress"
  | "deprecated"
  | "resolved"
  | "completed"
  | "default";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  active: "bg-canon-info-bg text-canon-info-fg",
  in_progress: "bg-canon-warning-bg text-canon-warning-fg",
  deprecated: "bg-canon-surface text-canon-text-secondary",
  resolved: "bg-canon-success-bg text-canon-success-fg",
  completed: "bg-canon-success-bg text-canon-success-fg",
  default: "bg-canon-surface text-canon-text-secondary",
};

export function Badge({ variant = "default", children, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center h-5 px-2 font-condensed font-bold text-xs uppercase tracking-[0.05em] ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
