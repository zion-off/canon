export type BadgeVariant =
  | "active"
  | "in_progress"
  | "deprecated"
  | "resolved"
  | "completed"
  | "default";

interface BadgeProps {
  variant?: string;
  children: React.ReactNode;
  className?: string;
}

const variantClasses: Record<string, string> = {
  active: "bg-canon-blue/15 text-canon-blue border-canon-blue/30",
  in_progress: "bg-canon-amber/15 text-canon-amber border-canon-amber/30",
  deprecated: "bg-white/5 text-canon-muted border-white/10",
  resolved: "bg-canon-green/15 text-canon-green border-canon-green/30",
  completed: "bg-canon-green/15 text-canon-green border-canon-green/30",
  default: "bg-white/5 text-canon-text-dim border-white/10",
};

export function Badge({
  variant = "default",
  children,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
