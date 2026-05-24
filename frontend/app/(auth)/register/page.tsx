"use client";

import { useActionState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "@/lib/actions/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface RegisterState {
  error: string | null;
  success: boolean;
}

const initialState: RegisterState = { error: null, success: false };

async function registerAction(
  _prevState: RegisterState,
  formData: FormData
): Promise<RegisterState> {
  const name = formData.get("name") as string;
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  if (!name || !email || !password) {
    return { error: "All fields are required.", success: false };
  }

  if (password.length < 8) {
    return { error: "Password must be at least 8 characters.", success: false };
  }

  try {
    await register(email, name, password);
    return { error: null, success: true };
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "An unexpected error occurred.";
    return { error: message, success: false };
  }
}

export default function RegisterPage() {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(
    registerAction,
    initialState
  );

  useEffect(() => {
    if (state.success) {
      router.push("/onboarding");
    }
  }, [state.success, router]);

  return (
    <div className="w-full max-w-md px-4">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-[Syne] font-bold text-slate-200 mb-2">
          Canon
        </h1>
        <p className="text-slate-400 text-sm">
          Organizational memory for engineering teams
        </p>
      </div>

      <div className="bg-[#0f0f1a] border border-white/[0.08] rounded-xl p-8">
        <form action={formAction} className="space-y-5">
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium text-slate-300 mb-1.5"
            >
              Name
            </label>
            <Input
              id="name"
              name="name"
              type="text"
              placeholder="Jane Smith"
              required
              autoComplete="name"
            />
          </div>

          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-slate-300 mb-1.5"
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
              className="block text-sm font-medium text-slate-300 mb-1.5"
            >
              Password
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder="••••••••"
              required
              autoComplete="new-password"
              minLength={8}
            />
            <p className="text-xs text-slate-500 mt-1">Minimum 8 characters</p>
          </div>

          {state.error && (
            <p
              role="alert"
              className="text-sm text-[#EF4444] bg-[#EF4444]/10 rounded-md px-3 py-2"
            >
              {state.error}
            </p>
          )}

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? "Creating account…" : "Create account"}
          </Button>
        </form>
      </div>

      <p className="text-center text-sm text-slate-400 mt-6">
        Already have an account?{" "}
        <Link
          href="/login"
          className="text-blue-500 hover:text-blue-400 transition-colors"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
