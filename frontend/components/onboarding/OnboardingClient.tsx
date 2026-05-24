"use client";

import { useActionState, useState, useEffect, useRef } from "react";
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
            <div role="tablist" className="flex border-b border-white/[0.08]">
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

function TabButton({
  id,
  panelId,
  active,
  onClick,
  children,
}: {
  id: string;
  panelId: string;
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      id={id}
      aria-selected={active}
      aria-controls={panelId}
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

interface CreateTeamState {
  error: string | null;
  token: string | null;
}

const createTeamInitialState: CreateTeamState = { error: null, token: null };

async function createTeamAction(
  _prevState: CreateTeamState,
  formData: FormData
): Promise<CreateTeamState> {
  const name = (formData.get("team-name") as string)?.trim();

  if (!name) {
    return { error: "Team name is required.", token: null };
  }

  try {
    const result = await createTeam(name);
    return { error: null, token: result.rawApiToken };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to create team.";
    return { error: message, token: null };
  }
}

function CreateTeamForm() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(
    createTeamAction,
    createTeamInitialState
  );

  if (state.token) {
    return (
      <div className="space-y-6">
        <ApiTokenDisplay token={state.token} />
        <Button onClick={() => router.push("/dashboard")} className="w-full">
          Go to Dashboard
        </Button>
      </div>
    );
  }

  return (
    <form action={formAction} className="space-y-5">
      <div>
        <label
          htmlFor="team-name"
          className="block text-sm font-medium text-slate-300 mb-1.5"
        >
          Team name
        </label>
        <Input
          id="team-name"
          name="team-name"
          type="text"
          placeholder="Acme Engineering"
          required
        />
      </div>

      {state.error && (
        <p
          role="alert"
          className="text-sm text-[#EF4444] bg-[#EF4444]/10 rounded-md px-3 py-2"
        >
          {state.error}
        </p>
      )}

      <Button type="submit" disabled={isPending} className="w-full">
        {isPending ? "Creating team…" : "Create team"}
      </Button>
    </form>
  );
}

interface JoinTeamState {
  error: string | null;
  teamName: string | null;
}

const joinTeamInitialState: JoinTeamState = { error: null, teamName: null };

async function joinTeamAction(
  _prevState: JoinTeamState,
  formData: FormData
): Promise<JoinTeamState> {
  const code = (formData.get("invite-code") as string)?.trim().toUpperCase();

  if (!code || code.length !== 8) {
    return { error: "Invite code must be 8 characters.", teamName: null };
  }

  try {
    const result = await joinTeam(code);
    return { error: null, teamName: result.teamName };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to join team.";
    return { error: message, teamName: null };
  }
}

function JoinTeamForm() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(
    joinTeamAction,
    joinTeamInitialState
  );
  const redirectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (state.teamName) {
      redirectTimer.current = setTimeout(() => router.push("/dashboard"), 1000);
    }
    return () => {
      if (redirectTimer.current) {
        clearTimeout(redirectTimer.current);
      }
    };
  }, [state.teamName, router]);

  if (state.teamName) {
    return (
      <div className="text-center py-4">
        <p className="text-lg font-medium text-slate-200">
          Joined {state.teamName}!
        </p>
        <p className="text-sm text-slate-400 mt-2">Redirecting to dashboard…</p>
      </div>
    );
  }

  return (
    <form action={formAction} className="space-y-5">
      <div>
        <label
          htmlFor="invite-code"
          className="block text-sm font-medium text-slate-300 mb-1.5"
        >
          Invite code
        </label>
        <Input
          id="invite-code"
          name="invite-code"
          type="text"
          placeholder="ABCD1234"
          required
          maxLength={8}
          className="uppercase tracking-widest"
        />
      </div>

      {state.error && (
        <p
          role="alert"
          className="text-sm text-[#EF4444] bg-[#EF4444]/10 rounded-md px-3 py-2"
        >
          {state.error}
        </p>
      )}

      <Button type="submit" disabled={isPending} className="w-full">
        {isPending ? "Joining…" : "Join team"}
      </Button>
    </form>
  );
}
