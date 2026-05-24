"use client";

import { useActionState } from "react";
import { useRouter } from "next/navigation";
import { createTeam } from "@/lib/actions/teams";
import { ROUTE_DASHBOARD } from "@/lib/constants";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiTokenDisplay } from "./ApiTokenDisplay";

interface CreateTeamState {
  error: string | null;
  token: string | null;
}

const initialState: CreateTeamState = { error: null, token: null };

async function createTeamAction(
  _prevState: CreateTeamState,
  formData: FormData,
): Promise<CreateTeamState> {
  const name = (formData.get("team-name") as string)?.trim();

  if (!name) {
    return { error: "Team name is required.", token: null };
  }

  try {
    const result = await createTeam(name);
    return { error: null, token: result.rawApiToken };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to create team.";
    return { error: message, token: null };
  }
}

export function CreateTeamForm() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(createTeamAction, initialState);

  if (state.token) {
    return (
      <div className="space-y-6">
        <ApiTokenDisplay token={state.token} />
        <Button onClick={() => router.push(ROUTE_DASHBOARD)} className="w-full">
          Go to Dashboard
        </Button>
      </div>
    );
  }

  return (
    <form action={formAction} className="space-y-5">
      <div>
        <label htmlFor="team-name" className="block text-sm font-medium text-canon-text mb-1.5">
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
        <p role="alert" className="text-sm text-canon-red bg-canon-red/10 rounded-md px-3 py-2">
          {state.error}
        </p>
      )}

      <Button type="submit" disabled={isPending} className="w-full">
        {isPending ? "Creating team…" : "Create team"}
      </Button>
    </form>
  );
}
