"use client";

import { useActionState, useEffect, useState } from "react";
import Link from "next/link";
import { createAccount } from "@/app/actions/auth";

interface Props {
  path: "membership" | "medical";
  signedIn: boolean;
  defaultPlan: string;
  defaultCode: string;
  plans: { id: string; name: string; priceCents: number; price: string; audience: string; includesBlueprint: boolean }[];
  addOns: { id: string; name: string; description: string; priceCents: number; price: string }[];
  provinces: { code: string; name: string; live: boolean }[];
  consentText: { terms: string; privacy: string; marketing: string; analytics: string; employer: string };
}

function Check({ name, required, children }: { name: string; required?: boolean; children: React.ReactNode }) {
  return (
    <label className="flex items-start gap-3 text-sm leading-6 text-ink-2">
      <input type="checkbox" name={name} required={required} className="mt-1 size-4 shrink-0 accent-ink" />
      <span>{children}</span>
    </label>
  );
}

export function JoinForm({ path, signedIn, defaultPlan, defaultCode, plans, addOns, provinces, consentText }: Props) {
  const [state, action, pending] = useActionState(createAccount, null);
  const [plan, setPlan] = useState(plans.some((p) => p.id === defaultPlan) ? defaultPlan : "core");
  const [chosen, setChosen] = useState<string[]>([]);
  const [code, setCode] = useState(defaultCode);
  const [assessment, setAssessment] = useState("");

  useEffect(() => {
    setAssessment(localStorage.getItem("reclaim.assessment.v1") ?? "");
  }, []);

  const p = plans.find((x) => x.id === plan)!;
  const visibleAddOns = addOns.filter((a) => !(a.id === "blueprint-session" && p?.includesBlueprint));
  const subtotal = (code ? 0 : p?.priceCents ?? 0) + visibleAddOns.filter((a) => chosen.includes(a.id)).reduce((s, a) => s + a.priceCents, 0);

  return (
    <form action={action} className="grid gap-10 lg:grid-cols-[1.3fr_0.7fr]">
      <input type="hidden" name="path" value={path} />
      <input type="hidden" name="assessment" value={assessment} />
      <div className="space-y-10">
        {path === "membership" && (
          <>
            <fieldset>
              <legend className="text-xl font-semibold">1 · Programme</legend>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {plans.map((x) => (
                  <label key={x.id} className={`cursor-pointer rounded-2xl border p-4 transition-colors ${plan === x.id ? "border-ink bg-ink text-paper" : "border-line bg-card hover:bg-bone/60"}`}>
                    <input type="radio" name="plan" value={x.id} checked={plan === x.id} onChange={() => setPlan(x.id)} className="sr-only" />
                    <span className="flex items-baseline justify-between">
                      <span className="font-semibold">{x.name}</span>
                      <span className="font-mono">{x.price}<span className="text-xs opacity-70">/mo</span></span>
                    </span>
                    <span className={`mt-1 block text-sm leading-5 ${plan === x.id ? "text-paper/75" : "text-ink-2"}`}>{x.audience}</span>
                  </label>
                ))}
              </div>
              {assessment && <p className="mt-3 text-sm text-moss">✓ Your assessment answers will be added to your Blueprint when you create your account.</p>}
            </fieldset>

            <fieldset>
              <legend className="text-xl font-semibold">2 · Add-ons <span className="text-sm font-normal text-muted">(optional)</span></legend>
              <div className="mt-4 space-y-2">
                {visibleAddOns.map((a) => (
                  <label key={a.id} className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-line bg-card p-4 has-checked:border-ink">
                    <span className="flex gap-3">
                      <input type="checkbox" name="addons" value={a.id} checked={chosen.includes(a.id)} onChange={() => setChosen((c) => (c.includes(a.id) ? c.filter((x) => x !== a.id) : [...c, a.id]))} className="mt-1 size-4 accent-ink" />
                      <span><span className="font-medium">{a.name}</span><span className="block text-sm text-ink-2">{a.description}</span></span>
                    </span>
                    <span className="font-mono text-sm">{a.price}</span>
                  </label>
                ))}
              </div>
              <div className="mt-4 max-w-xs">
                <label className="field-label" htmlFor="code">Employer sponsor code</label>
                <input id="code" name="code" className="input uppercase" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="Optional" />
                <p className="field-hint">Demo code: DEMO-EMPLOYER (sponsors Core)</p>
              </div>
            </fieldset>
          </>
        )}

        <fieldset>
          <legend className="text-xl font-semibold">{path === "membership" ? "3 · " : ""}Your account</legend>
          {signedIn ? (
            <p className="mt-3 text-sm text-ink-2">You&apos;re signed in. We&apos;ll use your existing account.</p>
          ) : (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div><label className="field-label" htmlFor="name">Name</label><input id="name" name="name" className="input" required autoComplete="name" /></div>
              <div><label className="field-label" htmlFor="email">Email</label><input id="email" name="email" type="email" className="input" required autoComplete="email" /></div>
              <div><label className="field-label" htmlFor="password">Password</label><input id="password" name="password" type="password" minLength={10} className="input" required autoComplete="new-password" /><p className="field-hint">At least 10 characters.</p></div>
            </div>
          )}
          <div className="mt-4 max-w-xs">
            <label className="field-label" htmlFor="province">Province or country where you&apos;ll use RECLAIM</label>
            <select id="province" name="province" className="input" defaultValue="ON" required>
              {provinces.map((x) => <option key={x.code} value={x.code}>{x.name}{x.live ? "" : " — waitlist"}</option>)}
            </select>
          </div>
        </fieldset>

        {!signedIn && (
          <fieldset className="space-y-3 rounded-2xl border border-line bg-card p-5">
            <legend className="px-1 text-sm font-semibold">Consents — each one is separate</legend>
            <Check name="terms" required>{consentText.terms} <Link href="/legal/terms" className="underline" target="_blank">Read</Link> <span className="text-ember">(required)</span></Check>
            <Check name="privacy" required>{consentText.privacy} <Link href="/legal/privacy" className="underline" target="_blank">Read</Link> <span className="text-ember">(required)</span></Check>
            <Check name="marketing">{consentText.marketing} <span className="text-muted">(optional)</span></Check>
            <Check name="analytics">{consentText.analytics} <span className="text-muted">(optional)</span></Check>
            {code && <Check name="employer_ack">{consentText.employer}</Check>}
            <p className="pt-1 text-xs text-muted">Medical-practice consents are asked separately, by the practice, only if you request medical care.</p>
          </fieldset>
        )}
      </div>

      <aside className="lg:sticky lg:top-24 lg:self-start">
        <div className="card p-6">
          {path === "membership" ? (
            <>
              <p className="eyebrow">Summary</p>
              <p className="mt-3 flex justify-between"><span>{p?.name} — first month</span><span className="font-mono">{code ? "Sponsored" : p?.price}</span></p>
              {visibleAddOns.filter((a) => chosen.includes(a.id)).map((a) => (
                <p key={a.id} className="mt-1 flex justify-between text-sm"><span>{a.name}</span><span className="font-mono">{a.price}</span></p>
              ))}
              <p className="mt-4 flex justify-between border-t border-line pt-3 font-semibold"><span>Subtotal</span><span className="font-mono">${(subtotal / 100).toFixed(2)}</span></p>
              <p className="mt-1 text-xs text-muted">Tax is calculated for your province on the next step, where you&apos;ll review the full agreement before paying.</p>
            </>
          ) : (
            <p className="text-sm text-ink-2">Free account. No payment. The medical practice&apos;s questionnaire opens next.</p>
          )}
          {state?.error && <p role="alert" className="mt-4 rounded-lg bg-ember-soft px-3 py-2 text-sm text-ember">{state.error}</p>}
          <button className="btn-primary mt-5 w-full" disabled={pending}>{pending ? "Working…" : path === "membership" ? "Continue to review" : "Create free account"}</button>
          <p className="mt-3 text-center text-xs text-muted">Nothing is charged until you agree on the next page.</p>
        </div>
      </aside>
    </form>
  );
}
