"use client";

import { useActionState } from "react";
import { submitLead, joinWaitlist, submitWtp, type FormState } from "@/app/actions/public";
import { JURISDICTIONS } from "@/config/site";
import { CONSENTS } from "@/config/consents";

function Result({ state }: { state: FormState }) {
  if (!state) return null;
  return (
    <p role="status" className={`rounded-xl px-4 py-3 text-sm ${state.ok ? "bg-moss-soft text-moss" : "bg-ember-soft text-ember"}`}>
      {state.message}
    </p>
  );
}

export function LeadForm({ kind, sizeLabel = "Organisation size", messageLabel = "What are you hoping to do?" }: { kind: "employer" | "enterprise" | "partner" | "research"; sizeLabel?: string; messageLabel?: string }) {
  const [state, action, pending] = useActionState(submitLead, null);
  if (state?.ok) return <Result state={state} />;
  return (
    <form action={action} className="grid gap-4 sm:grid-cols-2">
      <input type="hidden" name="kind" value={kind} />
      <div>
        <label className="field-label" htmlFor={`${kind}-name`}>Your name</label>
        <input id={`${kind}-name`} name="name" className="input" required autoComplete="name" />
      </div>
      <div>
        <label className="field-label" htmlFor={`${kind}-org`}>Organisation</label>
        <input id={`${kind}-org`} name="org" className="input" required autoComplete="organization" />
      </div>
      <div>
        <label className="field-label" htmlFor={`${kind}-email`}>Work email</label>
        <input id={`${kind}-email`} name="email" type="email" className="input" required autoComplete="email" />
      </div>
      <div>
        <label className="field-label" htmlFor={`${kind}-size`}>{sizeLabel}</label>
        <select id={`${kind}-size`} name="size" className="input">
          <option value="">Select</option>
          {["1-10", "11-49", "50-249", "250-999", "1000+"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <div className="sm:col-span-2">
        <label className="field-label" htmlFor={`${kind}-msg`}>{messageLabel}</label>
        <textarea id={`${kind}-msg`} name="message" rows={4} className="input" />
        <p className="field-hint">Please don&apos;t include anyone&apos;s health information.</p>
      </div>
      <div className="sm:col-span-2 flex flex-wrap items-center gap-4">
        <button className="btn-primary" disabled={pending}>
          {pending ? "Sending…" : "Send"}
        </button>
        <Result state={state} />
      </div>
    </form>
  );
}

export function WaitlistForm({ defaultJurisdiction = "" }: { defaultJurisdiction?: string }) {
  const [state, action, pending] = useActionState(joinWaitlist, null);
  if (state?.ok) return <Result state={state} />;
  return (
    <form action={action} className="grid gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="field-label" htmlFor="wl-email">Email</label>
          <input id="wl-email" name="email" type="email" className="input" required autoComplete="email" />
        </div>
        <div>
          <label className="field-label" htmlFor="wl-j">Where do you live?</label>
          <select id="wl-j" name="jurisdiction" className="input" defaultValue={defaultJurisdiction} required>
            <option value="">Select</option>
            {JURISDICTIONS.filter((j) => j.status !== "live").map((j) => (
              <option key={j.code} value={j.code}>
                {j.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="field-label" htmlFor="wl-fsa">First three characters of your postal code (or US state code) — optional</label>
        <input id="wl-fsa" name="fsa" className="input max-w-40 uppercase" maxLength={3} placeholder="e.g. V5K" />
        <p className="field-hint">Helps us decide where to recruit partner gyms first. We never ask for your full address here.</p>
      </div>
      <fieldset>
        <legend className="field-label">What are you interested in?</legend>
        <div className="flex flex-wrap gap-2">
          {[
            ["coaching", "Coaching"],
            ["medical", "Medical assessment"],
            ["local", "In-person sessions"],
            ["employer", "Through my employer"],
          ].map(([v, l]) => (
            <label key={v} className="flex cursor-pointer items-center gap-2 rounded-full border border-line-2 bg-card px-3 py-1.5 text-sm has-checked:border-ink has-checked:bg-ink has-checked:text-paper">
              <input type="checkbox" name="interests" value={v} className="sr-only" />
              {l}
            </label>
          ))}
        </div>
      </fieldset>
      <label className="flex items-start gap-3 text-sm leading-6 text-ink-2">
        <input type="checkbox" name="marketing" className="mt-1 size-4 accent-ink" />
        <span>{CONSENTS.marketing_email.text} <span className="text-muted">(Optional. Without this we&apos;ll only email you once, when we launch near you.)</span></span>
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button className="btn-primary" disabled={pending}>
          {pending ? "Joining…" : "Join the waitlist"}
        </button>
        <Result state={state} />
      </div>
    </form>
  );
}

export function WtpForm() {
  const [state, action, pending] = useActionState(submitWtp, null);
  if (state?.ok) return <Result state={state} />;
  const qs = [
    ["too_cheap", "So cheap you'd question the quality"],
    ["cheap", "A bargain — great value"],
    ["expensive", "Getting expensive, but you'd still consider it"],
    ["too_expensive", "Too expensive to consider"],
  ];
  return (
    <form action={action} className="grid gap-4">
      <p className="text-sm text-ink-2">
        For a monthly programme with a coach who knows your plan and two 30-minute video sessions a month, at what monthly price (CAD) would it be…
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {qs.map(([k, l]) => (
          <label key={k} className="text-sm">
            <span className="field-label">{l}</span>
            <span className="flex items-center gap-2">
              <span className="text-muted">$</span>
              <input name={k} type="number" min={0} max={5000} inputMode="numeric" className="input" required />
            </span>
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <button className="btn-ghost" disabled={pending}>
          Submit anonymously
        </button>
        <Result state={state} />
      </div>
    </form>
  );
}
