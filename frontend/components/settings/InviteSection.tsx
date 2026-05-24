"use client";

import { useActionState } from "react";
import { createInvite } from "@/lib/actions/teams";
import { Button } from "@/components/ui/Button";
import { CopyButton } from "@/components/ui/CopyButton";
import { formatShortDate } from "@/lib/date-utils";

interface InviteState {
  error: string | null;
  code: string | null;
  expiresAt: string | null;
}

const initialState: InviteState = {
  error: null,
  code: null,
  expiresAt: null,
};

async function inviteAction(_prevState: InviteState, _formData: FormData): Promise<InviteState> {
  void _prevState;
  void _formData;
  try {
    const result = await createInvite();
    return { error: null, code: result.code, expiresAt: result.expiresAt };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to create invite.";
    return { error: message, code: null, expiresAt: null };
  }
}

export function InviteSection() {
  const [state, formAction, isPending] = useActionState(inviteAction, initialState);

  return (
    <section className="rounded-lg border border-canon-border bg-canon-surface p-6">
      <h2 className="font-syne text-lg font-semibold text-canon-text mb-1">Invite Members</h2>
      <p className="text-sm text-canon-text-dim mb-4">
        Generate an invite code for your teammates to join.
      </p>

      <form action={formAction} className="space-y-4">
        {state.error && (
          <p role="alert" className="text-sm text-canon-red bg-canon-red/10 rounded-md px-3 py-2">
            {state.error}
          </p>
        )}

        {state.code ? (
          <div className="space-y-3">
            <div>
              <p className="text-xs font-medium text-canon-text-dim mb-1.5 uppercase tracking-wide">
                Invite Code
              </p>
              <div className="relative">
                <pre className="rounded-lg border border-canon-border bg-canon-surface-2 p-4 text-center">
                  <code className="text-2xl font-mono tracking-[0.25em] text-canon-text">
                    {state.code}
                  </code>
                </pre>
                <CopyButton text={state.code} className="absolute top-2 right-2" />
              </div>
            </div>
            {state.expiresAt && (
              <p className="text-xs text-canon-muted">Expires {formatShortDate(state.expiresAt)}</p>
            )}
          </div>
        ) : (
          <Button type="submit" disabled={isPending} size="sm">
            {isPending ? "Generating…" : "Generate invite code"}
          </Button>
        )}
      </form>
    </section>
  );
}
