import type { Metadata } from "next";
import Link from "next/link";
import { Container, EntityTag, SectionHeading } from "@/components/ui";
import type { EntityId } from "@/config/site";

export const metadata: Metadata = { title: "How it works" };

const STEPS: { n: string; h: string; who: EntityId; p: string; detail: string[] }[] = [
  {
    n: "01", h: "Free assessment", who: "platform",
    p: "Four minutes on goals, how you move, your week, food, sleep and what's got in the way. No weight or medical history.",
    detail: ["Answers stay in your browser until you join", "You see the reasons behind every suggestion", "Outside Ontario? Join the waitlist"],
  },
  {
    n: "02", h: "Blueprint session", who: "platform",
    p: "A 60-minute session with your coach turns the assessment into a written plan with three measurable targets.",
    detail: ["Baseline tests adapted to pain", "Schedule built around your real week", "Saved, versioned and visible in your portal"],
  },
  {
    n: "03", h: "Weekly plan", who: "platform",
    p: "Training at home, a partner gym or with a trainer; nutrition and sleep habits; short lessons. Your coach adjusts it every two weeks.",
    detail: ["Form checks: film a lift, your coach sends cues", "Message your coach during support hours", "Use credits at partner gyms and studios"],
  },
  {
    n: "04", h: "Medical assessment — only if you want one", who: "clinical",
    p: "Request a visit with a physician or nurse practitioner at the independent practice. They decide what, if anything, is appropriate.",
    detail: ["No membership needed", "OHIP-insured services are never charged to you", "Separate medical record and privacy notice"],
  },
  {
    n: "05", h: "Your pharmacy, your choice", who: "pharmacy",
    p: "If something is prescribed, choose any pharmacy. Our partner pharmacy can deliver; the price comes from the pharmacy you choose.",
    detail: ["Options shown in random order", "Pharmacist counselling before first fill", "Pharmacy bills your drug plan"],
  },
  {
    n: "06", h: "Measure, adjust, maintain", who: "platform",
    p: "Re-test every four weeks. When you reach your targets, move to Maintenance to keep them.",
    detail: ["Strength, waist, habits, optional scans", "Progress charts you can export", "Maintenance from month seven"],
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <Container className="py-16">
        <p className="eyebrow">How it works</p>
        <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05] sm:text-6xl">One plan. The right professional for each part of it.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">Each step is labelled with who is responsible for it. Medical steps are optional and separate.</p>
      </Container>
      <Container>
        <ol className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.n} className="card flex flex-col p-6">
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm text-ember">{s.n}</span>
                <EntityTag entity={s.who} />
              </div>
              <h2 className="mt-4 text-2xl">{s.h}</h2>
              <p className="mt-2 text-[15px] leading-7 text-ink-2">{s.p}</p>
              <ul className="mt-4 space-y-1.5 border-t border-line pt-4 text-sm text-ink-2">
                {s.detail.map((d) => <li key={d} className="flex gap-2"><span className="text-moss">·</span>{d}</li>)}
              </ul>
            </li>
          ))}
        </ol>
      </Container>
      <Container className="py-20">
        <div className="card flex flex-wrap items-center justify-between gap-6 p-8">
          <SectionHeading eyebrow="Form checks" title="Film a lift. See your form improve.">
            Record a short clip on your phone; it measures your joint angles and reps on the device, and your coach sends cues. Every check is saved to your record.
          </SectionHeading>
          <Link href="/assessment" className="btn-primary">Start the free assessment</Link>
        </div>
      </Container>
    </>
  );
}
