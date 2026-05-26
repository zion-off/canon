"use client";

import { useActionState } from "react";
import { createToken } from "@/lib/actions/teams";
import { CopyButton } from "@/components/ui/CopyButton";
import type { ApiToken } from "@/lib/schemas/teams";

interface TokenState {
  error: string | null;
  token: string | null;
  label: string | null;
}

const initialState: TokenState = { error: null, token: null, label: null };

async function tokenAction(_prevState: TokenState, formData: FormData): Promise<TokenState> {
  void _prevState;
  const label = (formData.get("token-label") as string)?.trim() || "API token";
  try {
    const result = await createToken(label);
    return { error: null, token: result.token, label: result.label };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to create token.";
    return { error: message, token: null, label: null };
  }
}

const labelClass = "font-condensed font-bold text-xs uppercase tracking-[0.08em]";

interface TokenSectionProps {
  onTokenAdded: (token: ApiToken) => void;
}

export function TokenSection({ onTokenAdded }: TokenSectionProps) {
  const [state, formAction, isPending] = useActionState(tokenAction, initialState);

  if (state.token) {
    return (
      <div className="space-y-2">
        <div className="flex items-center border border-canon-border">
          <pre className="flex-1 px-3 py-2 overflow-x-auto">
            <code className="text-sm font-mono text-canon-text">{state.token}</code>
          </pre>
          <CopyButton text={state.token} className="shrink-0 px-3" />
        </div>
        <div className="flex items-center justify-between">
          <span className={`${labelClass} text-canon-text-secondary`}>
            Won&apos;t be shown again
          </span>
          <button
            type="button"
            className={`${labelClass} text-canon-text hover:text-canon-text-secondary transition-colors cursor-pointer`}
            onClick={() =>
              onTokenAdded({
                id: crypto.randomUUID(),
                label: state.label ?? "API token",
                createdAt: new Date().toISOString(),
                lastUsedAt: null,
              })
            }
          >
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <form action={formAction}>
      {state.error && (
        <p role="alert" className={`${labelClass} text-canon-error mb-3`}>
          {state.error}
        </p>
      )}
      <div className="flex items-baseline gap-4">
        <input
          name="token-label"
          placeholder="Label"
          required
          className="w-40 bg-transparent border-b border-canon-border pb-1 text-sm text-canon-text placeholder:text-canon-text-secondary focus:outline-none focus:border-canon-accent transition-colors"
        />
        <button
          type="submit"
          disabled={isPending}
          className={`${labelClass} text-canon-text-secondary hover:text-canon-text disabled:opacity-[0.38] transition-colors cursor-pointer`}
        >
          {isPending ? "Creating…" : "Create"}
        </button>
      </div>
    </form>
  );
}
