const tabBase = "font-condensed font-bold text-xs uppercase tracking-[0.08em] pb-2 border-b-2";
const tabActive = "text-canon-text border-canon-text";
const tabInactive = "text-canon-text-secondary border-transparent";
const colHeader =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary";

export default function AppLoading() {
  return (
    <>
      <div className="flex items-center gap-4 border-b border-canon-border -mx-5 px-5 pt-3 sticky top-10 bg-canon-bg z-40">
        <span className={`${tabBase} ${tabActive}`}>
          Yours
          <span className="ml-1.5 inline-block h-3 w-3 animate-pulse bg-canon-border align-middle" />
        </span>
        <span className={`${tabBase} ${tabInactive}`}>
          Team
          <span className="ml-1.5 inline-block h-3 w-3 animate-pulse bg-canon-border align-middle" />
        </span>
      </div>

      <div className="-mx-5">
        <div className="grid grid-cols-[1fr_auto] gap-x-6 px-5 py-2 border-b border-canon-border">
          <span className={colHeader}>Session</span>
          <span className={`${colHeader} text-right`}>Last run</span>
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_auto] gap-x-6 items-center px-5 py-3 border-b border-canon-border"
          >
            <div className="space-y-2">
              <div className="h-8 w-64 animate-pulse bg-canon-border" />
              <div className="h-2 w-96 animate-pulse bg-canon-border" />
            </div>
            <div className="h-2 w-12 animate-pulse bg-canon-border" />
          </div>
        ))}
      </div>
    </>
  );
}
