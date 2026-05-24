"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createTeam, joinTeam } from "@/lib/actions/teams";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiTokenDisplay } from "./ApiTokenDisplay";

type Tab = "create" | "join";

export function OnboardingClient() {
  const [activeTab, setActiveTab] = useState<Tab>("create");

  return (
    <div className="min-h-screen bg-[#080810]">
      <header className="border-b border-white/[0.08] px-6 py-4">
        <span className="text-xl font-[Syne] font-bold text-slate-200">
          Canon
        </span>
      </header>

      <main className="flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-[Syne] font-semibold text-slate-200 mb-2">
              Welcome to Canon
            </h1>
            <p className="text-slate-400 text-sm">
              Create a new team or join an existing one to get started.
            </p>
          </div>

          <div className="bg-[#0f0f1a] border border-white/[0.08] rounded-xl overflow-hidden">
            <div className="flex border-b border-white/[0.08]">
              <TabButton
                active={activeTab === "create"}
                onClick={() => setActiveTab("create")}
              >
                Create a team
              </TabButton>
              <TabButton
                active={activeTab === "join"}
                onClick={() => setActiveTab("join")}
              >
                Join a team
              </TabButton>
            </div>

            <div className="p-8">
              {activeTab === "create" ? <CreateTeamForm /> : <JoinTeamForm />}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
        active
          ? "text-slate-200 bg-[#161625] border-b-2 border-blue-500"
          : "text-slate-400 hover:text-slate-300 hover:bg-white/[0.02]"
      }`}
    >
      {children}
    </button>
  );
}

function CreateTeamForm() {
  const router = useRouter();
  const [teamName, setTeamName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiToken, setApiToken] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (!teamName.trim()) {
      setError("Team name is required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await createTeam(teamName.trim());
      setApiToken(result.rawApiToken);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to create team.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (apiToken) {
    return (
      <div className="space-y-6">
        <ApiTokenDisplay token={apiToken} />
        <Button onClick={() => router.push("/dashboard")} className="w-full">
          Go to Dashboard
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label
          htmlFor="team-name"
          className="block text-sm font-medium text-slate-300 mb-1.5"
        >
          Team name
        </label>
        <Input
          id="team-name"
          type="text"
          value={teamName}
          onChange={(e) => setTeamName(e.target.value)}
          placeholder="Acme Engineering"
          required
        />
      </div>

      {error && (
        <p className="text-sm text-[#EF4444] bg-[#EF4444]/10 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Creating team…" : "Create team"}
      </Button>
    </form>
  );
}

function JoinTeamForm() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const trimmed = code.trim().toUpperCase();
    if (!trimmed || trimmed.length !== 8) {
      setError("Invite code must be 8 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await joinTeam(trimmed);
      setSuccessMessage(`Joined ${result.teamName}!`);
      setTimeout(() => router.push("/dashboard"), 1000);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to join team.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (successMessage) {
    return (
      <div className="text-center py-4">
        <p className="text-lg font-medium text-slate-200">{successMessage}</p>
        <p className="text-sm text-slate-400 mt-2">Redirecting to dashboard…</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label
          htmlFor="invite-code"
          className="block text-sm font-medium text-slate-300 mb-1.5"
        >
          Invite code
        </label>
        <Input
          id="invite-code"
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="ABCD1234"
          required
          maxLength={8}
          className="uppercase tracking-widest"
        />
      </div>

      {error && (
        <p className="text-sm text-[#EF4444] bg-[#EF4444]/10 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "Joining…" : "Join team"}
      </Button>
    </form>
  );
}
