import type { Metadata } from "next";
import Link from "next/link";
import { Container, SectionHeading, Notice, EntityTag } from "@/components/ui";
import { SITE } from "@/config/site";

export const metadata: Metadata = { title: "Coaching" };

export default function CoachingPage() {
  return (
    <>
      <Container className="py-16">
        <EntityTag entity="platform" />
        <h1 className="mt-5 max-w-3xl text-5xl font-medium leading-[1.05] sm:text-6xl">A coach who knows your plan — with clear limits on what that means.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
          RECLAIM coaches cover strength, nutrition habits and behaviour change. They work from your Blueprint, adjust it with your data, and know when to
          send you to a clinician, physiotherapist or dietitian instead.
        </p>
      </Container>
      <Container className="grid gap-5 md:grid-cols-3">
        {[
          ["Live sessions", "Scheduled 30-minute video sessions (Core: two a month; Premium: weekly). Reschedule up to 12 hours ahead."],
          ["Messages", `During support hours (${SITE.supportHours}). Replies within ${SITE.coachResponseSla} on Core and Hybrid. Not for urgent or medical questions.`],
          ["Plan updates", "Every two weeks based on what you log — sessions completed, tests, sleep and steps."],
        ].map(([h, p]) => (
          <div key={h} className="card p-6"><h2 className="text-2xl">{h}</h2><p className="mt-2 text-[15px] leading-7 text-ink-2">{p}</p></div>
        ))}
      </Container>
      <Container className="grid gap-10 py-16 lg:grid-cols-2">
        <SectionHeading eyebrow="Who coaches" title="Credentials you can check.">
          Coaches hold a recognised exercise or nutrition-coaching certification [specify accepted credentials, e.g. CSEP-CPT / CSEP-CEP, before launch] and
          complete RECLAIM method training. Each coach&apos;s caseload is capped so response times hold. If your coach is away, a named cover coach with access
          to your Blueprint takes over.
        </SectionHeading>
        <div className="space-y-4">
          <Notice title="What coaches don't do">
            Coaches don&apos;t diagnose, adjust or comment on medication, or interpret lab results. If you raise a symptom or side effect, they&apos;ll point you to
            the clinical team through Care → Messages, which goes to the medical practice.
          </Notice>
          <Notice tone="clinical" title="Your clinician and coach can work together — if you agree">
            With your permission, your clinician can share a short care summary (for example, exercise precautions) with your coach, and your coach&apos;s data
            can be shared with your clinician. Both are off until you turn them on.
          </Notice>
          <Link href="/programmes" className="btn-primary">See programmes</Link>
        </div>
      </Container>
    </>
  );
}
