"use client";

import { useActionState } from "react";
import { createInvite } from "@/lib/actions/teams";
import { CopyButton } from "@/components/ui/CopyButton";
import { formatShortDate } from "@/lib/date-utils";

interface InviteState {
  error: string | null;
  code: string | null;
  expiresAt: string | null;
}

const initialState: InviteState = { error: null, code: null, expiresAt: null };

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

const actionClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text-secondary hover:text-canon-text transition-colors cursor-pointer";

export function InviteSection() {
  const [state, formAction, isPending] = useActionState(inviteAction, initialState);

  if (state.code) {
    return (
      <div className="space-y-2">
        <div className="relative">
          <pre className="border-b border-canon-border py-3 text-center">
            <code className="font-mono text-2xl tracking-[0.25em] text-canon-text">
              {state.code}
            </code>
          </pre>
          <CopyButton text={state.code} className="absolute top-2 right-0" />
        </div>
        {state.expiresAt && (
          <p className="text-xs text-canon-text-secondary">
            Expires {formatShortDate(state.expiresAt)}
          </p>
        )}
      </div>
    );
  }

  return (
    <form action={formAction}>
      {state.error && (
        <p role="alert" className="text-xs text-canon-error mb-2">
          {state.error}
        </p>
      )}
      <button type="submit" disabled={isPending} className={actionClass}>
        {isPending ? "Generating…" : "Generate"}
      </button>
    </form>
  );
}
