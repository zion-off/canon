"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { z } from "zod";
import { login } from "@/lib/actions/auth";
import { ROUTE_DASHBOARD, ROUTE_REGISTER } from "@/lib/constants";

const formSchema = z.object({
  email: z.string().min(1, "Email is required."),
  password: z.string().min(1, "Password is required."),
});

const fieldClass =
  "w-full bg-transparent border-b border-canon-border py-2 text-sm text-canon-text placeholder:text-canon-text-secondary focus:outline-none focus:border-canon-accent transition-colors";
const actionClass =
  "font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text hover:text-canon-text-secondary transition-colors cursor-pointer disabled:opacity-[0.38]";

export default function LoginPage() {
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
    const { email, password } = parsed.data;

    setIsPending(true);
    setError(null);
    const result = await login(email, password);
    if (!result.success) {
      setError(result.error);
      setIsPending(false);
      return;
    }
    router.push(ROUTE_DASHBOARD);
  }

  return (
    <div className="w-72">
      <p className="font-condensed font-bold text-xs uppercase tracking-[0.08em] text-canon-text mb-10">
        canon
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
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
          autoComplete="current-password"
          className={fieldClass}
        />

        {error && (
          <p role="alert" className="text-xs text-canon-error">
            {error}
          </p>
        )}

        <button type="submit" disabled={isPending} className={actionClass}>
          {isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-10 text-xs text-canon-text-secondary">
        No account?{" "}
        <Link
          href={ROUTE_REGISTER}
          className="text-canon-text hover:text-canon-text-secondary transition-colors"
        >
          Register
        </Link>
      </p>
    </div>
  );
}
