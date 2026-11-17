"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  EMPTY_ANSWERS, GOAL_OPTIONS, BARRIER_OPTIONS, SETTING_OPTIONS, suggestPath,
  type AssessmentAnswers, type AssessmentResult,
} from "@/lib/assessment";
import { WtpForm } from "@/components/forms";

export const STORAGE_KEY = "reclaim.assessment.v1";

interface PlanSummary { id: string; name: string; price: string; includes: string[] }
interface Props {
  plans: PlanSummary[];
  liveCodes: string[];
  jurisdictions: { code: string; name: string; status: string }[];
}

function event(name: string, props: Record<string, string | number | boolean | null> = {}) {
  fetch("/api/events", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ name, props }), keepalive: true }).catch(() => {});
}

function Choice({ name, value, checked, onChange, children, type = "radio" }: { name: string; value: string; checked: boolean; onChange: () => void; children: React.ReactNode; type?: "radio" | "checkbox" }) {
  return (
    <label className={`flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 text-[15px] leading-6 transition-colors ${checked ? "border-ink bg-ink text-paper" : "border-line bg-card hover:border-line-2 hover:bg-bone/60"}`}>
      <input type={type} name={name} value={value} checked={checked} onChange={onChange} className="sr-only" />
      <span aria-hidden="true" className={`mt-1 grid size-4 shrink-0 place-items-center ${type === "radio" ? "rounded-full" : "rounded"} border ${checked ? "border-lime bg-lime" : "border-line-2"}`}>
        {checked && <span className={`${type === "radio" ? "size-1.5 rounded-full" : "size-2 rounded-[2px]"} bg-ink`} />}
      </span>
      <span>{children}</span>
    </label>
  );
}

function Q({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <fieldset className="mb-8">
      <legend className="mb-1 text-lg font-semibold">{title}</legend>
      {hint && <p className="mb-3 text-sm text-muted">{hint}</p>}
      <div className="mt-3 grid gap-2">{children}</div>
    </fieldset>
  );
}

const STEPS = ["Goals", "Movement today", "Your week", "Food, sleep & stress", "What gets in the way", "Medical care & location"];

export function Assessment({ plans, liveCodes, jurisdictions }: Props) {
  const [a, setA] = useState<AssessmentAnswers>(EMPTY_ANSWERS);
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [started, setStarted] = useState(false);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
      if (saved?.answers) {
        setA({ ...EMPTY_ANSWERS, ...saved.answers });
        if (saved.result) setResult(saved.result);
        setRestored(true);
      }
    } catch {}
  }, []);

  const set = <K extends keyof AssessmentAnswers>(k: K, v: AssessmentAnswers[K]) => {
    if (!started) {
      setStarted(true);
      event("assessment_started", {});
    }
    setA((prev) => ({ ...prev, [k]: v }));
  };
  const toggle = (k: "goals" | "barriers" | "setting", v: string) => set(k, a[k].includes(v) ? a[k].filter((x) => x !== v) : [...a[k], v]);

  const canNext = useMemo(() => {
    switch (step) {
      case 0: return a.goals.length > 0;
      case 1: return !!(a.activity && a.experience && a.sitToStand && a.pain);
      case 2: return a.setting.length > 0;
      case 3: return !!(a.cookingTime && a.stress);
      case 4: return !!a.coachingStyle;
      case 5: return !!(a.medicalInterest && a.jurisdiction);
      default: return false;
    }
  }, [a, step]);

  const finish = () => {
    const r = suggestPath(a, liveCodes);
    setResult(r);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ answers: a, result: r, completedAt: new Date().toISOString() }));
    event("assessment_completed", { jurisdiction: a.jurisdiction });
    event("path_suggested", { plan: r.plan, jurisdiction: a.jurisdiction, medical_interest: a.medicalInterest });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const restart = () => {
    localStorage.removeItem(STORAGE_KEY);
    setA(EMPTY_ANSWERS);
    setResult(null);
    setStep(0);
    setRestored(false);
  };

  if (result) {
    const plan = plans.find((p) => p.id === result.plan)!;
    return (
      <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="eyebrow">Your suggested starting point</p>
          <h1 className="mt-3 text-5xl font-medium leading-tight">{result.available ? plan.name : "You're early — we're not in your area yet"}</h1>
          {result.available ? (
            <p className="mt-3 font-mono text-xl">{plan.price} <span className="text-sm text-muted">/month + HST · pilot price</span></p>
          ) : (
            <p className="mt-3 text-lg text-ink-2">RECLAIM is available in Ontario first. Join the waitlist and we&apos;ll tell you when we open near you.</p>
          )}

          <h2 className="mt-10 font-sans text-sm font-semibold uppercase tracking-wider text-muted">Why we suggested this</h2>
          <ul className="mt-3 space-y-3">
            {result.reasons.map((r) => (
              <li key={r} className="flex gap-3 text-[15px] leading-7 text-ink-2">
                <span className="mt-2.5 size-1.5 shrink-0 rounded-full bg-ember" />
                {r}
              </li>
            ))}
          </ul>

          <h2 className="mt-10 font-sans text-sm font-semibold uppercase tracking-wider text-muted">Where your Blueprint would likely start</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {result.focus.map((f) => (
              <div key={f.title} className="card p-4">
                <p className="font-semibold">{f.title}</p>
                <p className="mt-1 text-sm leading-6 text-ink-2">{f.detail}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm text-muted">Baseline tests: {result.baselineTests.join(" · ")}</p>

          <div className="mt-8 rounded-xl border border-line bg-bone/60 p-4 text-sm leading-6 text-ink-2">
            This is general programme guidance based on your preferences — not a medical assessment, diagnosis or treatment recommendation. Your answers are stored only in this browser until you create an account.
          </div>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
          <div className="card p-6">
            {result.available ? (
              <>
                <p className="font-semibold">{plan.name} includes</p>
                <ul className="mt-3 space-y-2 text-sm">
                  {plan.includes.map((i) => (
                    <li key={i} className="flex gap-2"><span className="text-moss">✓</span>{i}</li>
                  ))}
                </ul>
                <Link href={`/join?plan=${plan.id}&from=assessment`} className="btn-primary mt-6 w-full">Start with {plan.name}</Link>
                <Link href="/programmes" className="btn-ghost mt-2 w-full">Compare all programmes</Link>
                {result.medicalPointer && (
                  <p className="mt-4 text-xs leading-5 text-muted">
                    Only want the medical assessment? You can <Link className="underline" href="/join?path=medical">create a free account</Link> and request one without a membership.
                  </p>
                )}
              </>
            ) : (
              <Link href={`/waitlist?j=${a.jurisdiction}`} className="btn-primary w-full">Join the waitlist</Link>
            )}
          </div>
          <details className="card p-6">
            <summary className="cursor-pointer font-semibold">Help us set fair prices (optional, anonymous)</summary>
            <div className="mt-4"><WtpForm /></div>
          </details>
          <button onClick={restart} className="text-sm text-muted underline">Clear my answers and start again</button>
        </aside>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <p className="eyebrow">Step {step + 1} of {STEPS.length} · {STEPS[step]}</p>
          {restored && <button onClick={restart} className="text-xs text-muted underline">Start over</button>}
        </div>
        <div className="mt-3 flex gap-1.5" aria-hidden="true">
          {STEPS.map((s, i) => (
            <div key={s} className={`h-1 flex-1 rounded-full ${i <= step ? "bg-ink" : "bg-line"}`} />
          ))}
        </div>
      </div>

      {step === 0 && (
        <Q title="What do you want from the next six months?" hint="Choose all that apply.">
          {GOAL_OPTIONS.map((g) => (
            <Choice key={g.id} type="checkbox" name="goals" value={g.id} checked={a.goals.includes(g.id)} onChange={() => toggle("goals", g.id)}>{g.label}</Choice>
          ))}
        </Q>
      )}

      {step === 1 && (
        <>
          <Q title="How active are you in a typical week?">
            {[["none", "Rarely active"], ["some", "Some walking or occasional exercise"], ["regular", "Exercise most weeks"]].map(([v, l]) => (
              <Choice key={v} name="activity" value={v} checked={a.activity === v} onChange={() => set("activity", v as AssessmentAnswers["activity"])}>{l}</Choice>
            ))}
          </Q>
          <Q title="Experience with strength training?">
            {[["new", "New to it"], ["some", "Some — on and off"], ["experienced", "Experienced"]].map(([v, l]) => (
              <Choice key={v} name="experience" value={v} checked={a.experience === v} onChange={() => set("experience", v as AssessmentAnswers["experience"])}>{l}</Choice>
            ))}
          </Q>
          <Q title="Can you stand up from a dining chair without using your hands?">
            {[["easily", "Yes, easily"], ["with_effort", "Yes, with effort"], ["needs_hands", "Not without my hands"], ["unsure", "Not sure"]].map(([v, l]) => (
              <Choice key={v} name="sts" value={v} checked={a.sitToStand === v} onChange={() => set("sitToStand", v as AssessmentAnswers["sitToStand"])}>{l}</Choice>
            ))}
          </Q>
          <Q title="Does pain limit how you move?">
            {[["none", "No"], ["some", "Sometimes — I work around it"], ["significant", "Yes, significantly"]].map(([v, l]) => (
              <Choice key={v} name="pain" value={v} checked={a.pain === v} onChange={() => set("pain", v as AssessmentAnswers["pain"])}>{l}</Choice>
            ))}
          </Q>
        </>
      )}

      {step === 2 && (
        <>
          <Q title={`How many days a week can you realistically train? ${a.daysPerWeek}`}>
            <input type="range" min={1} max={6} value={a.daysPerWeek} onChange={(e) => set("daysPerWeek", Number(e.target.value))} className="w-full accent-ink" aria-label="Days per week" />
          </Q>
          <Q title="How long per session?">
            <div className="grid grid-cols-4 gap-2">
              {[20, 30, 45, 60].map((m) => (
                <Choice key={m} name="mins" value={String(m)} checked={a.minutesPerSession === m} onChange={() => set("minutesPerSession", m)}>{m} min</Choice>
              ))}
            </div>
          </Q>
          <Q title="Where would you like to train?" hint="Choose all that apply.">
            {SETTING_OPTIONS.map((s) => (
              <Choice key={s.id} type="checkbox" name="setting" value={s.id} checked={a.setting.includes(s.id)} onChange={() => toggle("setting", s.id)}>{s.label}</Choice>
            ))}
          </Q>
        </>
      )}

      {step === 3 && (
        <>
          <Q title="Time you have for cooking on a weekday?">
            {[["low", "Under 15 minutes"], ["medium", "15–30 minutes"], ["high", "More than 30 minutes"]].map(([v, l]) => (
              <Choice key={v} name="cook" value={v} checked={a.cookingTime === v} onChange={() => set("cookingTime", v as AssessmentAnswers["cookingTime"])}>{l}</Choice>
            ))}
          </Q>
          <Q title="Any eating pattern we should plan around?" hint="Optional.">
            <input className="input" value={a.eatingPattern} onChange={(e) => set("eatingPattern", e.target.value)} placeholder="e.g. vegetarian, halal, shift work, intermittent fasting" />
          </Q>
          <Q title={`Average sleep on a work night: ${a.sleepHours} hours`}>
            <input type="range" min={4} max={10} step={0.5} value={a.sleepHours} onChange={(e) => set("sleepHours", Number(e.target.value))} className="w-full accent-ink" aria-label="Sleep hours" />
          </Q>
          <Q title="Day-to-day stress?">
            {[["low", "Low"], ["medium", "Moderate"], ["high", "High"]].map(([v, l]) => (
              <Choice key={v} name="stress" value={v} checked={a.stress === v} onChange={() => set("stress", v as AssessmentAnswers["stress"])}>{l}</Choice>
            ))}
          </Q>
        </>
      )}

      {step === 4 && (
        <>
          <Q title="What has got in the way before?" hint="Choose all that apply.">
            <div className="grid gap-2 sm:grid-cols-2">
              {BARRIER_OPTIONS.map((b) => (
                <Choice key={b.id} type="checkbox" name="barriers" value={b.id} checked={a.barriers.includes(b.id)} onChange={() => toggle("barriers", b.id)}>{b.label}</Choice>
              ))}
            </div>
          </Q>
          <Q title="What kind of support do you want?">
            {[
              ["self", "A good plan — I'll mostly do it myself"],
              ["check_ins", "A coach who checks in and adjusts my plan"],
              ["live", "Regular live video sessions with a coach"],
              ["in_person", "In-person sessions at a gym or with a trainer"],
            ].map(([v, l]) => (
              <Choice key={v} name="style" value={v} checked={a.coachingStyle === v} onChange={() => set("coachingStyle", v as AssessmentAnswers["coachingStyle"])}>{l}</Choice>
            ))}
          </Q>
        </>
      )}

      {step === 5 && (
        <>
          <Q
            title="Would you like a clinician to review whether medical care is appropriate for you?"
            hint="An independent physician or nurse practitioner decides — not this questionnaire. Medical care is separate from any membership and is never automatic."
          >
            {[["yes", "Yes"], ["maybe", "Maybe — I'd like to learn more"], ["no", "No, coaching only"]].map(([v, l]) => (
              <Choice key={v} name="med" value={v} checked={a.medicalInterest === v} onChange={() => set("medicalInterest", v as AssessmentAnswers["medicalInterest"])}>{l}</Choice>
            ))}
          </Q>
          <Q title="Where do you live?">
            <select className="input" value={a.jurisdiction} onChange={(e) => set("jurisdiction", e.target.value)} aria-label="Province or country">
              <option value="">Select</option>
              {jurisdictions.map((j) => (
                <option key={j.code} value={j.code}>{j.name}{j.status !== "live" ? " — waitlist" : ""}</option>
              ))}
            </select>
          </Q>
        </>
      )}

      <div className="flex items-center justify-between border-t border-line pt-6">
        <button className="btn-ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>Back</button>
        {step < STEPS.length - 1 ? (
          <button className="btn-primary" onClick={() => setStep((s) => s + 1)} disabled={!canNext}>Continue</button>
        ) : (
          <button className="btn-primary" onClick={finish} disabled={!canNext}>See my suggested programme</button>
        )}
      </div>
      <p className="mt-6 text-center text-xs text-muted">Your answers are saved only in this browser. We record anonymous step counts to improve the questionnaire.</p>
    </div>
  );
}
