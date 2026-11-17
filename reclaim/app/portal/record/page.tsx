import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { memberRecord, type RecordKind } from "@/lib/record";
import { PageHeader, MembershipRequired } from "@/components/portal";
import { fmtDate } from "@/lib/money";

const KIND: Record<RecordKind, { label: string; dot: string }> = {
  milestone: { label: "Milestone", dot: "bg-lime ring-2 ring-ink" },
  form: { label: "Form check", dot: "bg-series" },
  measure: { label: "Measurement", dot: "bg-moss" },
  blueprint: { label: "Blueprint", dot: "bg-ember" },
  session: { label: "Session", dot: "bg-clinic" },
  week: { label: "Week", dot: "bg-line-2" },
  membership: { label: "Membership", dot: "bg-ink" },
};

export default async function RecordPage() {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const { events, summary } = memberRecord(user.id);
  const months = new Map<string, typeof events>();
  for (const e of events) {
    const k = fmtDate(e.at, { month: "long", year: "numeric" });
    months.set(k, [...(months.get(k) ?? []), e]);
  }
  const stats: Array<[string, string | number]> = [
    ["Weeks in the programme", summary.weeks],
    ["Form checks", summary.formChecks],
    ["Measurements", summary.measurements],
    ["Personal bests", summary.personalBests],
    ["Sessions completed", summary.sessions],
  ];

  return (
    <>
      <PageHeader eyebrow={summary.since ? `Member since ${fmtDate(summary.since)}` : "Your record"} title="My record" actions={<a href="/api/export" className="btn-ghost btn-sm">Download everything</a>}>
        Everything you&apos;ve done in RECLAIM, saved in one place: form checks and coach feedback, measurements, Blueprint changes, sessions and milestones.
      </PageHeader>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {stats.map(([l, v]) => (
          <div key={l} className="card p-4">
            <p className="text-2xl font-semibold">{v}</p>
            <p className="mt-0.5 text-xs text-muted">{l}</p>
          </div>
        ))}
      </div>

      <div className="space-y-8">
        {[...months.entries()].map(([month, list]) => (
          <section key={month}>
            <h2 className="eyebrow mb-3">{month}</h2>
            <ol className="relative space-y-1 border-l border-line pl-5">
              {list.map((e, i) => (
                <li key={`${e.at}-${i}`} className="relative">
                  <span className={`absolute -left-[25px] top-3 size-2.5 rounded-full ${KIND[e.kind].dot}`} aria-hidden="true" />
                  <div className={`rounded-xl px-3 py-2 ${e.kind === "milestone" ? "bg-lime/30" : "hover:bg-card"}`}>
                    <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
                      <span className="font-medium">{e.href ? <Link href={e.href} className="hover:underline">{e.title}</Link> : e.title}</span>
                      <span className="text-xs text-muted">{KIND[e.kind].label} · {fmtDate(e.at, { month: "short", day: "numeric" })}</span>
                    </p>
                    {e.detail && <p className="mt-0.5 text-sm text-ink-2">{e.detail}</p>}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
      <p className="mt-8 text-xs text-muted">Medical care is recorded by the independent practice and shown in Care, not here.</p>
    </>
  );
}
