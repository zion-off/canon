import { getGraph } from "@/lib/actions/graph";
import { MemoryGraphClient } from "@/components/graph/MemoryGraphClient";

export const metadata = {
  title: "Memory Graph — Canon",
  description: "Visualize organizational memory as a force-directed graph",
};

export default async function GraphPage() {
  const graphData = await getGraph();

  const nodeCount = graphData.nodes.length;
  const linkCount = graphData.links.length;

  return (
    <div className="flex h-full flex-col">
      <header className="shrink-0 border-b border-white/[0.08] px-6 py-4">
        <h1 className="font-[Syne,sans-serif] text-2xl font-semibold text-slate-200">
          Organizational Memory
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {nodeCount} nodes · {linkCount} relationships
        </p>
      </header>

      <div className="min-h-0 flex-1">
        <MemoryGraphClient graphData={graphData} />
      </div>
    </div>
  );
}
