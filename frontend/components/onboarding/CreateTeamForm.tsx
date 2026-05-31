"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { createTeam } from "@/lib/actions/teams";
import { ROUTE_ONBOARDING_SETUP } from "@/lib/constants";

const formSchema = z.object({
  "team-name": z.string().min(1, "Team name is required."),
});

const fieldClass =
  "w-full bg-transparent border-b border-canon-border py-2 text-sm text-canon-text placeholder:text-canon-text-secondary focus:outline-none focus:border-canon-accent transition-colors";
const actionClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text hover:text-canon-text-secondary transition-colors cursor-pointer disabled:opacity-[0.38]";

export function CreateTeamForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    const parsed = formSchema.safeParse(Object.fromEntries(new FormData(e.currentTarget)));
    if (!parsed.success) {
      setError(parsed.error.errors[0].message);
      return;
    }
    const { "team-name": name } = parsed.data;

    setIsPending(true);
    setError(null);
    try {
      const result = await createTeam(name);
      sessionStorage.setItem("onboarding_token", result.rawApiToken);
      router.push(ROUTE_ONBOARDING_SETUP);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create team.");
      setIsPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <input
        name="team-name"
        type="text"
        placeholder="Team"
        required
        autoComplete="off"
        className={fieldClass}
      />

      {error && (
        <p role="alert" className="text-xs text-canon-error">
          {error}
        </p>
      )}

      <button type="submit" disabled={isPending} className={actionClass}>
        {isPending ? "Creating…" : "Create team"}
      </button>
    </form>
  );
}
