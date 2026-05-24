import type { Metadata } from "next";
import { getGraph } from "@/lib/actions/graph";
import { MemoryGraphClient } from "@/components/graph/MemoryGraphClient";

export const metadata: Metadata = {
  title: "Memory Graph — Canon",
  description: "Visualize organizational memory as a force-directed graph",
};

export default async function GraphPage() {
  const graphData = await getGraph();

  const nodeCount = graphData.nodes.length;
  const linkCount = graphData.links.length;

  return (
    <div className="flex h-full flex-col">
      <header className="shrink-0 border-b border-canon-border px-6 py-4">
        <h1 className="font-syne text-2xl font-semibold text-canon-text">
          Organizational Memory
        </h1>
        <p className="mt-1 text-sm text-canon-text-dim">
          {nodeCount} nodes · {linkCount} relationships
        </p>
      </header>

      <div className="min-h-0 flex-1">
        <MemoryGraphClient graphData={graphData} />
      </div>
    </div>
  );
}
