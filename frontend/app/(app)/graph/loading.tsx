const inputBase =
  "bg-transparent border-b border-canon-border py-1.5 font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary";

export default function GraphLoading() {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center gap-3 border-b border-canon-border py-3">
        <div className={`w-40 ${inputBase}`}>Filter by tag…</div>
        <div className={`w-48 ${inputBase}`}>Search memories…</div>
        <span className="ml-auto font-condensed font-bold text-xs uppercase tracking-wider text-canon-text-secondary">
          <span className="inline-block h-3 w-8 animate-pulse bg-canon-border align-middle" />{" "}
          memories ·{" "}
          <span className="inline-block h-3 w-8 animate-pulse bg-canon-border align-middle" />{" "}
          connections
        </span>
      </div>

      <div
        className="flex min-h-0 flex-1 bg-canon-bg"
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(212, 212, 212, 0.08) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />
    </div>
  );
}
