"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "@/lib/actions/auth";
import { ROUTE_LOGIN, ROUTE_ONBOARDING } from "@/lib/constants";

const fieldClass =
  "w-full bg-transparent border-b border-canon-border py-2 text-sm text-canon-text placeholder:text-canon-text-secondary focus:outline-none focus:border-canon-accent transition-colors";
const actionClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text hover:text-canon-text-secondary transition-colors cursor-pointer disabled:opacity-[0.38]";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const name = data.get("name") as string;
    const email = data.get("email") as string;
    const password = data.get("password") as string;

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setIsPending(true);
    setError(null);
    try {
      await register(email, name, password);
      router.push(ROUTE_ONBOARDING);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
      setIsPending(false);
    }
  }

  return (
    <div className="w-72">
      <p className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text mb-10">
        canon
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <input
          name="name"
          type="text"
          placeholder="Name"
          required
          autoComplete="name"
          className={fieldClass}
        />
        <input
          name="email"
          type="email"
          placeholder="you@company.com"
          required
          autoComplete="email"
          className={fieldClass}
        />
        <input
          name="password"
          type="password"
          placeholder="••••••••"
          required
          autoComplete="new-password"
          minLength={8}
          className={fieldClass}
        />

        {error && (
          <p role="alert" className="text-xs text-canon-error">
            {error}
          </p>
        )}

        <button type="submit" disabled={isPending} className={actionClass}>
          {isPending ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="mt-10 text-xs text-canon-text-secondary">
        Already have an account?{" "}
        <Link
          href={ROUTE_LOGIN}
          className="text-canon-text hover:text-canon-text-secondary transition-colors"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
