"use client";

import { useActionState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { joinTeam } from "@/lib/actions/teams";
import { ROUTE_DASHBOARD } from "@/lib/constants";

interface JoinTeamState {
  error: string | null;
  teamName: string | null;
}

const initialState: JoinTeamState = { error: null, teamName: null };

async function joinTeamAction(
  _prevState: JoinTeamState,
  formData: FormData,
): Promise<JoinTeamState> {
  const inviteCodeSchema = z.string().length(8, "Invite code must be 8 characters.");
  const rawCode = formData.get("invite-code");
  const parsed = inviteCodeSchema.safeParse(typeof rawCode === "string" ? rawCode.toUpperCase() : rawCode);
  if (!parsed.success) return { error: parsed.error.errors[0].message, teamName: null };
  const code = parsed.data;
  try {
    const result = await joinTeam(code);
    return { error: null, teamName: result.team.name };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to join team.";
    return { error: message, teamName: null };
  }
}

const fieldClass =
  "w-full bg-transparent border-b border-canon-border py-2 text-sm text-canon-text placeholder:text-canon-text-secondary focus:outline-none focus:border-canon-accent transition-colors lowercase tracking-widest";
const actionClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text hover:text-canon-text-secondary transition-colors cursor-pointer disabled:opacity-[0.38]";

export function JoinTeamForm() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(joinTeamAction, initialState);
  const redirectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (state.teamName) {
      redirectTimer.current = setTimeout(() => router.push(ROUTE_DASHBOARD), 1000);
    }
    return () => {
      if (redirectTimer.current) clearTimeout(redirectTimer.current);
    };
  }, [state.teamName, router]);

  if (state.teamName) {
    return (
      <p className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary">
        Joined {state.teamName} — redirecting…
      </p>
    );
  }

  return (
    <form action={formAction} className="space-y-6">
      <input
        name="invite-code"
        type="text"
        placeholder="ABCD1234"
        required
        maxLength={8}
        autoComplete="off"
        className={fieldClass}
      />

      {state.error && (
        <p role="alert" className="text-xs text-canon-error">
          {state.error}
        </p>
      )}

      <button type="submit" disabled={isPending} className={actionClass}>
        {isPending ? "Joining…" : "Join team"}
      </button>
    </form>
  );
}
