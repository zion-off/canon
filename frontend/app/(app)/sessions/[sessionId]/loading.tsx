const labelClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em]";

export default function SessionLoading() {
  return (
    <>
      <div className="h-10 flex items-center gap-3 border-b border-canon-border -mx-5 px-5 sticky top-10 bg-canon-bg z-40">
        <span className={`${labelClass} text-canon-text-secondary`}>Sessions</span>
        <span className={`${labelClass} text-canon-text-disabled`}>·</span>
        <span className={`${labelClass} text-canon-text truncate animate-pulse bg-canon-border h-4 w-48 rounded`} />
      </div>

      <div className="pt-8 pb-4">
        <div className="h-12 w-96 animate-pulse bg-canon-border rounded mb-2" />
        <div className="h-4 w-64 animate-pulse bg-canon-border rounded" />
      </div>

      <div className="space-y-6 pt-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-3">
            <div className="h-4 w-32 animate-pulse bg-canon-border rounded" />
            <div className="space-y-2">
              <div className="h-4 w-full animate-pulse bg-canon-border rounded" />
              <div className="h-4 w-5/6 animate-pulse bg-canon-border rounded" />
              <div className="h-4 w-3/4 animate-pulse bg-canon-border rounded" />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
