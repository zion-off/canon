const labelClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em]";

const sectionLabels = ["Invite Members", "MCP Config", "API Tokens"];

export default function SettingsLoading() {
  return (
    <div>
      <div className="h-10 flex items-center border-b border-canon-border -mx-5 px-5">
        <span className={`${labelClass} text-canon-text`}>Settings</span>
      </div>

      <div className="-mx-5">
        {sectionLabels.map((label) => (
          <div key={label} className="grid grid-cols-[1fr_2fr] border-b border-canon-border">
            <div className="px-5 py-6 border-r border-canon-border">
              <span className={`${labelClass} text-canon-text-secondary`}>{label}</span>
            </div>
            <div className="px-5 py-6">
              <div className="h-4 w-48 animate-pulse bg-canon-border" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
