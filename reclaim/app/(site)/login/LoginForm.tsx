"use client";

import { useActionState } from "react";
import { login } from "@/app/actions/auth";

export function LoginForm({ next }: { next: string }) {
  const [state, action, pending] = useActionState(login, null);
  return (
    <form action={action} className="space-y-4">
      <input type="hidden" name="next" value={next} />
      <div>
        <label className="field-label" htmlFor="email">Email</label>
        <input id="email" name="email" type="email" className="input" required autoComplete="email" />
      </div>
      <div>
        <label className="field-label" htmlFor="password">Password</label>
        <input id="password" name="password" type="password" className="input" required autoComplete="current-password" />
      </div>
      {state?.error && <p role="alert" className="rounded-lg bg-ember-soft px-3 py-2 text-sm text-ember">{state.error}</p>}
      <button type="submit" className="btn-primary w-full" disabled={pending}>{pending ? "Logging in…" : "Log in"}</button>
    </form>
  );
}
