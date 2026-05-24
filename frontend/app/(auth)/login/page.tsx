"use client";

import { useActionState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/actions/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface LoginState {
  error: string | null;
  success: boolean;
}

const initialState: LoginState = { error: null, success: false };

async function loginAction(
  _prevState: LoginState,
  formData: FormData
): Promise<LoginState> {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  if (!email || !password) {
    return { error: "Email and password are required.", success: false };
  }

  try {
    await login(email, password);
    return { error: null, success: true };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred.";
    return { error: message, success: false };
  }
}

export default function LoginPage() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(
    loginAction,
    initialState
  );

  useEffect(() => {
    if (state.success) {
      router.push("/dashboard");
    }
  }, [state.success, router]);

  return (
    <div className="w-full max-w-md px-4">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-syne font-bold text-canon-text mb-2">
          Canon
        </h1>
        <p className="text-canon-text-dim text-sm">
          Organizational memory for engineering teams
        </p>
      </div>

      <div className="bg-canon-surface border border-canon-border rounded-xl p-8">
        <form action={formAction} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-canon-text mb-1.5"
            >
              Email
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="you@company.com"
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-canon-text mb-1.5"
            >
              Password
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              required
              autoComplete="current-password"
            />
          </div>

          {state.error && (
            <p
              role="alert"
              className="text-sm text-canon-red bg-canon-red/10 rounded-md px-3 py-2"
            >
              {state.error}
            </p>
          )}

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>

      <p className="text-center text-sm text-canon-text-dim mt-6">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="text-canon-blue hover:text-canon-blue/80 transition-colors"
        >
          Register
        </Link>
      </p>
    </div>
  );
}
