import type { Metadata } from "next";
import { getGraph } from "@/lib/actions/graph";
import { MemoryGraphClient } from "@/components/graph/MemoryGraphClient";

export const metadata: Metadata = {
  title: "Memory Graph — canon",
  description: "Visualize organizational memory as a force-directed graph",
};

export default async function GraphPage() {
  const graphData = await getGraph();

  return <MemoryGraphClient graphData={graphData} />;
}
