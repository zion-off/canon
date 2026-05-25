import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone output is for production Docker builds only
  ...(process.env.NODE_ENV === "production" && { output: "standalone" }),
};

export default nextConfig;
