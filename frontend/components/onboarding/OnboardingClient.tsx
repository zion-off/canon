"use client";

import { useState } from "react";
import { CreateTeamForm } from "./CreateTeamForm";
import { JoinTeamForm } from "./JoinTeamForm";

type Tab = "create" | "join";

const wordmarkClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text";
const toggleClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] cursor-pointer transition-colors";

export function OnboardingClient() {
  const [activeTab, setActiveTab] = useState<Tab>("create");

  return (
    <div className="min-h-screen flex items-center justify-center px-5">
      <div className="w-xl">
        <p className={`${wordmarkClass} mb-10`}>canon</p>

        <div className="flex gap-4 mb-8">
          <button
            type="button"
            onClick={() => setActiveTab("create")}
            className={`${toggleClass} ${activeTab === "create" ? "text-canon-text" : "text-canon-text-secondary hover:text-canon-text"}`}
          >
            Create a team
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("join")}
            className={`${toggleClass} ${activeTab === "join" ? "text-canon-text" : "text-canon-text-secondary hover:text-canon-text"}`}
          >
            Join a team
          </button>
        </div>

        {activeTab === "create" ? <CreateTeamForm /> : <JoinTeamForm />}
      </div>
    </div>
  );
}
