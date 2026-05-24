"use client";

import { useState } from "react";
import { TabButton } from "./TabButton";
import { CreateTeamForm } from "./CreateTeamForm";
import { JoinTeamForm } from "./JoinTeamForm";

type Tab = "create" | "join";

export function OnboardingClient() {
  const [activeTab, setActiveTab] = useState<Tab>("create");

  return (
    <div className="min-h-screen bg-canon-bg">
      <header className="border-b border-canon-border px-6 py-4">
        <span className="text-xl font-syne font-bold text-canon-text">Canon</span>
      </header>

      <main className="flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-syne font-semibold text-canon-text mb-2">
              Welcome to Canon
            </h1>
            <p className="text-canon-text-dim text-sm">
              Create a new team or join an existing one to get started.
            </p>
          </div>

          <div className="bg-canon-surface border border-canon-border rounded-xl overflow-hidden">
            <div role="tablist" className="flex border-b border-canon-border">
              <TabButton
                id="tab-create"
                panelId="panel-create"
                active={activeTab === "create"}
                onClick={() => setActiveTab("create")}
              >
                Create a team
              </TabButton>
              <TabButton
                id="tab-join"
                panelId="panel-join"
                active={activeTab === "join"}
                onClick={() => setActiveTab("join")}
              >
                Join a team
              </TabButton>
            </div>

            <div
              role="tabpanel"
              id={activeTab === "create" ? "panel-create" : "panel-join"}
              aria-labelledby={activeTab === "create" ? "tab-create" : "tab-join"}
              className="p-8"
            >
              {activeTab === "create" ? <CreateTeamForm /> : <JoinTeamForm />}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
