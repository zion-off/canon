"use client";

import { useActionState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { joinTeam } from "@/lib/actions/teams";
import { ROUTE_DASHBOARD } from "@/lib/constants";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface JoinTeamState {
  error: string | null;
  teamName: string | null;
}

const initialState: JoinTeamState = { error: null, teamName: null };

async function joinTeamAction(
  _prevState: JoinTeamState,
  formData: FormData,
): Promise<JoinTeamState> {
  const code = (formData.get("invite-code") as string)?.trim().toUpperCase();

  if (!code || code.length !== 8) {
    return { error: "Invite code must be 8 characters.", teamName: null };
  }

  try {
    const result = await joinTeam(code);
    return { error: null, teamName: result.team.name };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to join team.";
    return { error: message, teamName: null };
  }
}

export function JoinTeamForm() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(joinTeamAction, initialState);
  const redirectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (state.teamName) {
      redirectTimer.current = setTimeout(() => router.push(ROUTE_DASHBOARD), 1000);
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
        <p className="text-lg font-medium text-canon-text">Joined {state.teamName}!</p>
        <p className="text-sm text-canon-text-dim mt-2">Redirecting to dashboard…</p>
      </div>
    );
  }

  return (
    <form action={formAction} className="space-y-5">
      <div>
        <label htmlFor="invite-code" className="block text-sm font-medium text-canon-text mb-1.5">
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
        <p role="alert" className="text-sm text-canon-red bg-canon-red/10 rounded-md px-3 py-2">
          {state.error}
        </p>
      )}

      <Button type="submit" disabled={isPending} className="w-full">
        {isPending ? "Joining…" : "Join team"}
      </Button>
    </form>
  );
}
