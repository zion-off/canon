export default function AppLoading() {
  return (
    <div className="space-y-8">
      <header>
        <div className="h-8 w-40 animate-pulse rounded-md bg-canon-surface-2" />
        <div className="mt-2 h-4 w-64 animate-pulse rounded-md bg-canon-surface-2" />
      </header>

      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border border-canon-border bg-canon-surface px-5 py-4">
            <div className="flex items-center justify-between">
              <div className="h-5 w-48 animate-pulse rounded-md bg-canon-surface-2" />
              <div className="h-4 w-16 animate-pulse rounded-md bg-canon-surface-2" />
            </div>
            <div className="mt-3 h-4 w-full animate-pulse rounded-md bg-canon-surface-2" />
          </div>
        ))}
      </div>
    </div>
  );
}
