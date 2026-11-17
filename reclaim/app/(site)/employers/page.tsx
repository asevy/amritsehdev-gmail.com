import type { Metadata } from "next";
import { Container, SectionHeading, Notice } from "@/components/ui";
import { LeadForm } from "@/components/forms";

export const metadata: Metadata = { title: "Employers" };

export default function EmployersPage() {
  return (
    <>
      <Container className="py-16">
        <p className="eyebrow">For employers · pilot programme</p>
        <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05] sm:text-6xl">Sponsor strength and metabolic health for your team.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
          Employees join with a sponsor code and get the same programme as everyone else. You get participation and aggregate outcome reporting — never
          an individual&apos;s data.
        </p>
      </Container>
      <Container className="grid gap-5 md:grid-cols-3">
        {[
          ["What employees get", "A sponsored Core membership: Blueprint session, coach, form checks, progress tracking. Optional local-network credits."],
          ["What you see", "Enrolment counts and de-identified, aggregate engagement and outcome measures, only for groups of 10 or more. Medical care is never reported."],
          ["How it's priced", "Per enrolled employee per month, invoiced monthly, with no minimum during the pilot. [Pricing to be set after pilot cost data.]"],
        ].map(([h, p]) => (
          <div key={h} className="card p-6"><h2 className="text-2xl">{h}</h2><p className="mt-2 text-[15px] leading-7 text-ink-2">{p}</p></div>
        ))}
      </Container>
      <Container className="grid gap-10 py-16 lg:grid-cols-2">
        <div className="space-y-4">
          <SectionHeading eyebrow="Privacy" title="Your employees' trust is the product." />
          <Notice>
            Employees&apos; health and coaching information is never shared with their employer. Use of the programme can&apos;t affect employment decisions,
            and employees can leave the sponsored programme at any time. Medical care from the independent practice is entirely separate.
          </Notice>
          <Notice tone="warn" title="Not yet available">
            Employer programmes are in design. Tell us about your organisation and we&apos;ll contact you about the pilot — we haven&apos;t signed any employer
            yet.
          </Notice>
        </div>
        <div className="card p-6">
          <p className="mb-4 font-semibold">Talk to us about a pilot</p>
          <LeadForm kind="employer" sizeLabel="Number of employees" messageLabel="What would success look like for you?" />
        </div>
      </Container>
    </>
  );
}
