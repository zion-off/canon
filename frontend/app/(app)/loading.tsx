export default function AppLoading() {
  return (
    <div className="pt-10">
      <div className="h-10 flex items-center border-b border-canon-border -mx-5 px-5">
        <div className="h-2 w-20 animate-pulse bg-canon-border" />
      </div>
      <div className="-mx-5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_auto_auto] gap-x-6 items-center px-5 py-3 border-b border-canon-border"
          >
            <div className="space-y-2">
              <div className="h-8 w-64 animate-pulse bg-canon-border" />
              <div className="h-2 w-96 animate-pulse bg-canon-border" />
            </div>
            <div className="h-4 w-12 animate-pulse bg-canon-border" />
            <div className="h-2 w-16 animate-pulse bg-canon-border" />
          </div>
        ))}
      </div>
    </div>
  );
}
