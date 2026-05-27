"use client";

import Link from "next/link";
import BarcodeWave from "./BarcodeWave";
import { ROUTE_LOGIN } from "@/lib/constants";

export default function LandingPage() {
  return (
    <div className="relative w-full h-screen bg-canon-bg overflow-hidden flex items-center justify-center">
      <div className="w-full h-1/3 relative">
        <BarcodeWave />

        <Link
          href={ROUTE_LOGIN}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 md:left-auto md:right-1/5 md:translate-x-0 -translate-y-1/2 font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text hover:text-canon-text-secondary transition-colors whitespace-nowrap"
        >
          Explore your canon
        </Link>
      </div>
    </div>
  );
}
