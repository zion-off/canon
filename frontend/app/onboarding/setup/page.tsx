"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiTokenDisplay } from "@/components/onboarding/ApiTokenDisplay";
import { ROUTE_DASHBOARD } from "@/lib/constants";

const actionClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text hover:text-canon-text-secondary transition-colors cursor-pointer";

export default function OnboardingSetupPage() {
  const router = useRouter();
  const [token] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    const stored = sessionStorage.getItem("onboarding_token");
    sessionStorage.removeItem("onboarding_token");
    return stored;
  });

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-5">
        <button type="button" onClick={() => router.push(ROUTE_DASHBOARD)} className={actionClass}>
          Go to dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-5">
      <div className="w-xl space-y-8">
        <p className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text">
          canon
        </p>
        <ApiTokenDisplay token={token} />
        <button type="button" onClick={() => router.push(ROUTE_DASHBOARD)} className={actionClass}>
          Go to dashboard
        </button>
      </div>
    </div>
  );
}
