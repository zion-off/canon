"use client";

import { useActionState, useState } from "react";
import { createToken } from "@/lib/actions/teams";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { CopyButton } from "@/components/ui/CopyButton";
import type { ApiToken } from "@/lib/schemas/teams";
import { formatShortDate } from "@/lib/date-utils";

interface TokenState {
  error: string | null;
  token: string | null;
  label: string | null;
}

const initialState: TokenState = {
  error: null,
  token: null,
  label: null,
};

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

interface TokenSectionProps {
  initialTokens: ApiToken[];
}

export function TokenSection({ initialTokens }: TokenSectionProps) {
  const [state, formAction, isPending] = useActionState(tokenAction, initialState);
  const [tokens, setTokens] = useState(initialTokens);

  return (
    <section className="rounded-lg border border-canon-border bg-canon-surface p-6">
      <h2 className="font-syne text-lg font-semibold text-canon-text mb-1">API Tokens</h2>
      <p className="text-sm text-canon-text-dim mb-4">
        Create tokens for your coding harness to connect to Canon.
      </p>

      <form action={formAction} className="space-y-4">
        {state.error && (
          <p role="alert" className="text-sm text-canon-red bg-canon-red/10 rounded-md px-3 py-2">
            {state.error}
          </p>
        )}

        {state.token ? (
          <div className="space-y-3 border border-canon-border rounded-lg p-4 bg-canon-surface-2">
            <p className="text-xs font-medium text-canon-text-dim uppercase tracking-wide">
              New Token — {state.label}
            </p>
            <p className="text-sm text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-md px-3 py-2">
              Save this token — it won&apos;t be shown again
            </p>
            <div className="relative">
              <pre className="rounded-lg border border-canon-border bg-canon-bg p-3 overflow-x-auto">
                <code className="text-sm font-mono text-canon-text break-all">{state.token}</code>
              </pre>
              <CopyButton text={state.token} className="absolute top-2 right-2" />
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() =>
                setTokens((prev) => [
                  ...prev,
                  {
                    id: "",
                    label: state.label ?? "API token",
                    createdAt: new Date().toISOString(),
                    lastUsedAt: null,
                  },
                ])
              }
            >
              Done
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <Input
              name="token-label"
              label="Token label"
              placeholder="Production harness"
              required
            />
            <Button type="submit" disabled={isPending} size="sm">
              {isPending ? "Creating…" : "Create token"}
            </Button>
          </div>
        )}
      </form>

      {tokens.length > 0 && (
        <div className="mt-6 border-t border-canon-border pt-4">
          <h3 className="text-sm font-medium text-canon-text mb-3">Existing tokens</h3>
          <ul className="space-y-2">
            {tokens.map((t) => (
              <li
                key={t.id || t.label}
                className="flex items-center justify-between rounded-md bg-canon-surface-2 px-3 py-2"
              >
                <div>
                  <p className="text-sm text-canon-text">{t.label}</p>
                  <p className="text-xs text-canon-muted">
                    Created {formatShortDate(t.createdAt)}
                    {t.lastUsedAt && ` · Last used ${formatShortDate(t.lastUsedAt)}`}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
