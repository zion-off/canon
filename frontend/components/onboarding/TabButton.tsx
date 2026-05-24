"use client";

interface TabButtonProps {
  id: string;
  panelId: string;
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

export function TabButton({ id, panelId, active, onClick, children }: TabButtonProps) {
  return (
    <button
      type="button"
      role="tab"
      id={id}
      aria-selected={active}
      aria-controls={panelId}
      onClick={onClick}
      className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
        active
          ? "text-canon-text bg-canon-surface-2 border-b-2 border-canon-blue"
          : "text-canon-text-dim hover:text-canon-text hover:bg-white/[0.02]"
      }`}
    >
      {children}
    </button>
  );
}
