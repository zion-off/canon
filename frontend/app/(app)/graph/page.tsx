import type { Metadata } from "next";
import { getGraph } from "@/lib/actions/graph";
import { MemoryGraphClient } from "@/components/graph/MemoryGraphClient";

export const metadata: Metadata = {
  title: "Memory Graph — canon",
  description: "Visualize organizational memory as a force-directed graph",
};

export default async function GraphPage() {
  const graphData = await getGraph();

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 40px)" }}>
      <div className="min-h-0 flex-1">
        <MemoryGraphClient graphData={graphData} />
      </div>
    </div>
  );
}
