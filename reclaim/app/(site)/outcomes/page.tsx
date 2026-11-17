import type { Metadata } from "next";
import { Container, Notice } from "@/components/ui";

export const metadata: Metadata = { title: "Outcomes & methods" };

const METRICS = [
  ["Retention", "% of members still active at weeks 4, 12 and 26", "All members"],
  ["Adherence", "Planned sessions completed ÷ planned, weeks 1–12", "All members"],
  ["Lower-body strength", "Change in 30-second sit-to-stand, baseline → week 12", "Members completing both tests"],
  ["Waist circumference", "Change baseline → week 12, standardised self-measurement protocol", "Members completing both"],
  ["Body composition", "Change in lean and fat mass where partner scans are taken under standard conditions", "Opt-in subgroup"],
  ["Habits", "Sleep duration, average daily steps", "Members logging ≥ 4 of 7 days"],
  ["Safety", "Pain flags, injuries, side-effect reports and how quickly the right professional responded", "All members / patients"],
];

export default function OutcomesPage() {
  return (
    <Container className="py-16">
      <p className="eyebrow">Outcomes & methods</p>
      <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05]">How we&apos;ll measure whether RECLAIM works.</h1>
      <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
        We&apos;re publishing the measures before the results, so we can&apos;t choose the flattering ones later. Results will be reported for everyone who
        started, not just those who finished.
      </p>
      <div className="mt-8"><Notice tone="warn" title="No results yet">The first report will follow the first pilot cohort to week 12. Until then, this page lists methods only.</Notice></div>
      <div className="mt-10 overflow-x-auto rounded-2xl border border-line bg-card">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Pre-specified outcome measures</caption>
          <thead className="bg-bone text-xs uppercase tracking-wider text-muted">
            <tr><th className="p-4">Measure</th><th className="p-4">Definition</th><th className="p-4">Population</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {METRICS.map(([a, b, c]) => <tr key={a}><td className="p-4 font-semibold">{a}</td><td className="p-4 text-ink-2">{b}</td><td className="p-4 text-ink-2">{c}</td></tr>)}
          </tbody>
        </table>
      </div>
      <div className="mt-10 grid gap-5 md:grid-cols-3">
        {[
          ["Intention-to-treat", "Everyone who starts is counted, including people who leave. Missing data is reported, not hidden."],
          ["Aggregate only", "Results are reported for groups, never individuals, with small groups suppressed."],
          ["Medical care reported separately", "Outcomes for patients of the independent practice are reported by the practice under its own governance."],
        ].map(([h, p]) => <div key={h} className="card p-5"><p className="font-semibold">{h}</p><p className="mt-1 text-sm leading-6 text-ink-2">{p}</p></div>)}
      </div>
    </Container>
  );
}
