import type { Metadata } from "next";
import { Container } from "@/components/ui";
import { LoginForm } from "./LoginForm";
import { SITE } from "@/config/site";
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "@/lib/db/seed";

export const metadata: Metadata = { title: "Log in" };

const ROLE_NOTE: Record<string, string> = {
  member: "Member portal: record, Blueprint, plan, progress, form checks, care, billing, privacy",
  coach: "Coach desk: review and record form checks, messages, consented care summary",
  clinician: "Clinician desk: queue, chart, prescribe from formulary",
  pharmacist: "Pharmacy desk: verify, counsel, price, ship",
  admin: "Founder insights: funnel, price test, capacity, outbox, audit",
};

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next } = await searchParams;
  return (
    <Container className="grid gap-12 py-16 lg:grid-cols-2">
      <div className="mx-auto w-full max-w-md lg:mx-0">
        <p className="eyebrow">Welcome back</p>
        <h1 className="mt-3 text-4xl font-medium">Log in</h1>
        <div className="card mt-8 p-6">
          <LoginForm next={next ?? ""} />
        </div>
        <p className="mt-4 text-sm text-muted">New here? <a className="underline" href="/assessment">Take the free assessment</a> or <a className="underline" href="/programmes">choose a programme</a>.</p>
      </div>
      {SITE.demoMode && (
        <div className="rounded-2xl border border-dashed border-line-2 bg-bone/50 p-6">
          <p className="eyebrow">Demo accounts · prototype only</p>
          <p className="mt-2 text-sm text-ink-2">Password for all: <code className="rounded bg-card px-1.5 py-0.5 font-mono">{DEMO_PASSWORD}</code></p>
          <ul className="mt-4 space-y-3">
            {DEMO_ACCOUNTS.map((a) => (
              <li key={a.email} className="text-sm">
                <code className="font-mono text-[13px]">{a.email}</code>
                <span className="ml-2 chip border-line-2 bg-card text-muted">{a.role}</span>
                <p className="mt-0.5 text-xs text-muted">{ROLE_NOTE[a.role]}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Container>
  );
}
