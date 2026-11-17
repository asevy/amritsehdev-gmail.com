import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { db, verifyAuditChain } from "@/lib/db";
import { activeVariant } from "@/lib/commerce";
import { pharmacyRevenueSummary } from "@/lib/pharmacy";
import { vanWestendorp } from "@/lib/assessment";
import { PLANS } from "@/config/catalog";
import { JURISDICTIONS } from "@/config/site";
import { setPriceVariant } from "@/app/actions/staff";
import { logout } from "@/app/actions/auth";
import { BarList } from "@/components/charts";
import { Logo, EntityTag, Notice, Stat } from "@/components/ui";
import { Panel } from "@/components/portal";
import { cad, cadExact, fmtDateTime } from "@/lib/money";

/** Wilson 95% interval for a proportion. */
function wilson(k: number, n: number): [number, number] {
  if (n === 0) return [0, 0];
  const z = 1.96, p = k / n, d = 1 + (z * z) / n;
  const c = (p + (z * z) / (2 * n)) / d, h = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}
const pct = (x: number) => `${(x * 100).toFixed(0)}%`;

/** Coaching capacity assumption — productive client-facing + async minutes per coach FTE per month. To validate in pilot time studies. */
const COACH_PRODUCTIVE_MIN_PER_FTE_MONTH = 110 * 60;

export default async function AdminPage({ searchParams }: { searchParams: Promise<{ synthetic?: string }> }) {
  await requireUser(["admin"]);
  const { synthetic } = await searchParams;
  const incl = synthetic === "1";
  const P = db("platform");
  const evWhere = incl ? "1=1" : "COALESCE(json_extract(props_json,'$.source'),'') <> 'synthetic'";
  const distinct = (name: string, extra = "") =>
    (P.prepare(`SELECT COUNT(DISTINCT COALESCE(anon_id, user_id)) AS n FROM events WHERE name = ? AND ${evWhere} ${extra}`).get(name) as { n: number }).n;

  const funnel = [
    ["Assessment started", "assessment_started"], ["Assessment completed", "assessment_completed"], ["Join started", "join_started"],
    ["Account created", "account_created"], ["Order reviewed", "order_review_viewed"], ["Paid", "order_paid"],
  ].map(([label, name]) => ({ label, value: distinct(name) }));
  const funnelRows = funnel.map((f, i) => ({ ...f, note: i === 0 ? "top of funnel" : `${funnel[i - 1].value ? pct(f.value / funnel[i - 1].value) : "—"} of previous step` }));

  const variant = activeVariant();
  const byVariant = [0, 1].map((v) => {
    const reviewed = distinct("order_review_viewed", `AND json_extract(props_json,'$.variant') = ${v}`);
    const paid = distinct("order_paid", `AND json_extract(props_json,'$.variant') = ${v}`);
    return { v, reviewed, paid, ci: wilson(paid, reviewed) };
  });

  const paths = P.prepare(`SELECT json_extract(props_json,'$.plan') AS plan, COUNT(*) AS n FROM events WHERE name = 'path_suggested' AND ${evWhere} GROUP BY plan ORDER BY n DESC`).all() as Array<{ plan: string; n: number }>;
  const med = P.prepare(`SELECT json_extract(props_json,'$.medical_interest') AS m, COUNT(*) AS n FROM events WHERE name = 'path_suggested' AND ${evWhere} GROUP BY m`).all() as Array<{ m: string; n: number }>;
  const medTotal = med.reduce((s, r) => s + r.n, 0);
  const medYes = med.filter((r) => r.m === "yes" || r.m === "maybe").reduce((s, r) => s + r.n, 0);

  const wlWhere = incl ? "1=1" : "email NOT LIKE '%@example.test'";
  const waitlist = P.prepare(`SELECT jurisdiction, COUNT(*) AS n, GROUP_CONCAT(DISTINCT fsa) AS fsas FROM waitlist WHERE ${wlWhere} GROUP BY jurisdiction ORDER BY n DESC`).all() as Array<{ jurisdiction: string; n: number; fsas: string | null }>;
  const leads = P.prepare(`SELECT kind, COUNT(*) AS n FROM leads WHERE ${wlWhere} GROUP BY kind`).all() as Array<{ kind: string; n: number }>;
  const doors = distinct("fake_door_clicked");
  const wtpRows = P.prepare(`SELECT too_cheap, cheap, expensive, too_expensive FROM wtp_responses WHERE ${incl ? "1=1" : "COALESCE(anon_id,'') NOT LIKE 'synthetic-%'"}`).all() as Array<{ too_cheap: number; cheap: number; expensive: number; too_expensive: number }>;
  const vw = vanWestendorp(wtpRows);

  // Capacity: derive coaching workload from active memberships (real data only).
  const active = P.prepare("SELECT plan_id, COUNT(*) AS n, SUM(CASE WHEN started_at > ? THEN 1 ELSE 0 END) AS new_n FROM subscriptions WHERE status = 'active' GROUP BY plan_id").all(new Date(Date.now() - 30 * 86400_000).toISOString()) as Array<{ plan_id: string; n: number; new_n: number }>;
  const capacity = active.map((a) => {
    const plan = PLANS.find((p) => p.id === a.plan_id)!;
    const mins = a.n * (plan.workload.liveMinutesPerMonth + plan.workload.asyncMinutesPerMonth) + a.new_n * plan.workload.blueprintMinutesOnce;
    return { plan: plan.name, members: a.n, minutes: mins };
  });
  const totalMin = capacity.reduce((s, c) => s + c.minutes, 0);

  const platformRev = P.prepare("SELECT COUNT(*) AS n, COALESCE(SUM(total_cents - tax_cents),0) AS net, COALESCE(SUM(tax_cents),0) AS tax FROM orders WHERE status = 'paid'").get() as { n: number; net: number; tax: number };
  const refunds = P.prepare("SELECT COUNT(*) AS n, COALESCE(SUM(amount_cents),0) AS c FROM refunds").get() as { n: number; c: number };
  const pharm = pharmacyRevenueSummary();
  const outbox = P.prepare("SELECT to_email, entity_id, class, subject, created_at FROM email_outbox ORDER BY id DESC LIMIT 8").all() as Array<{ to_email: string; entity_id: string; class: string; subject: string; created_at: string }>;
  const openRequests = (P.prepare("SELECT COUNT(*) AS n FROM data_requests WHERE status = 'open'").get() as { n: number }).n;
  const chainBreak = verifyAuditChain("platform");

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line bg-card">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
          <div className="flex items-center gap-4"><Link href="/"><Logo /></Link><span className="text-sm font-semibold">Founder insights</span><EntityTag entity="platform" /></div>
          <form action={logout}><button className="text-sm underline">Log out</button></form>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl space-y-6 px-5 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-medium">What the site is telling us</h1>
            <p className="mt-1 max-w-2xl text-sm text-ink-2">First-party, aggregate data for the business plan&apos;s open questions: demand, price, attachment and capacity. No clinical data is visible here.</p>
          </div>
          <Link href={incl ? "/admin" : "/admin?synthetic=1"} className="btn-ghost btn-sm">{incl ? "Exclude synthetic demo data" : "Include synthetic demo data"}</Link>
        </div>
        {incl && <Notice tone="warn" title="Showing synthetic demo data">Generated by the seed script so the dashboards can be explored. It is not evidence of demand and must never be cited as such.</Notice>}

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Acquisition funnel (distinct visitors)">
            <BarList rows={funnelRows} />
          </Panel>
          <Panel title="Sequential price test" action={<span className="text-xs text-muted">live: variant {variant === 0 ? "A (control)" : "B"}</span>}>
            <div className="grid grid-cols-2 gap-4">
              {byVariant.map((b) => (
                <Stat key={b.v} label={`Variant ${b.v === 0 ? "A" : "B"} review → paid`} value={b.reviewed ? pct(b.paid / b.reviewed) : "—"} sub={`${b.paid}/${b.reviewed} · 95% CI ${pct(b.ci[0])}–${pct(b.ci[1])}`} />
              ))}
            </div>
            <table className="mt-4 w-full text-xs">
              <thead className="text-left text-muted"><tr><th className="py-1 font-medium">Plan</th><th className="py-1 text-right font-medium">A</th><th className="py-1 text-right font-medium">B</th><th className="py-1 text-right font-medium">Status</th></tr></thead>
              <tbody>{PLANS.map((p) => <tr key={p.id} className="border-t border-line"><td className="py-1">{p.name}</td><td className="text-right tabular-nums">{cad(p.variantPriceCents[0])}</td><td className="text-right tabular-nums">{cad(p.variantPriceCents[1])}</td><td className="text-right">{p.priceStatus}</td></tr>)}</tbody>
            </table>
            <form action={setPriceVariant} className="mt-4 flex items-center gap-2 text-sm">
              <select name="variant" defaultValue={String(variant)} className="input max-w-48"><option value="0">A — control</option><option value="1">B — higher</option></select>
              <button className="btn-primary btn-sm">Set live price for all visitors</button>
            </form>
            <p className="mt-2 text-xs text-muted">One price is live for everyone at a time; switch weekly and compare periods. Overlapping intervals mean no conclusion yet.</p>
          </Panel>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Panel title="Willingness to pay (Van Westendorp)">
            {!vw ? <p className="text-sm text-muted">No responses yet.</p> : (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <Stat label="Too cheap below" value={vw.pointOfMarginalCheapness != null ? `$${vw.pointOfMarginalCheapness}` : "—"} />
                  <Stat label="Optimal" value={vw.optimalPricePoint != null ? `$${vw.optimalPricePoint}` : "—"} />
                  <Stat label="Indifference" value={vw.indifferencePricePoint != null ? `$${vw.indifferencePricePoint}` : "—"} />
                  <Stat label="Too expensive above" value={vw.pointOfMarginalExpensiveness != null ? `$${vw.pointOfMarginalExpensiveness}` : "—"} />
                </div>
                <p className="mt-3 text-xs text-muted">n = {vw.n}. Monthly coaching (Core-like offer), CAD. Stated preference only — validate against paid conversion.</p>
              </>
            )}
          </Panel>
          <Panel title="Medical-care interest (attachment signal)">
            <Stat label="Yes or maybe" value={medTotal ? pct(medYes / medTotal) : "—"} sub={`${medYes} of ${medTotal} completed assessments`} />
            <p className="mt-3 text-xs text-muted">Interest in a clinician review — not a prescription rate. Drives the medical arm&apos;s capacity model; never shown per clinician.</p>
            <div className="mt-4"><BarList rows={paths.map((p) => ({ label: `Suggested: ${p.plan}`, value: p.n }))} /></div>
          </Panel>
          <Panel title="B2B & fake doors">
            <ul className="space-y-2 text-sm">
              {["employer", "enterprise", "partner", "research"].map((k) => <li key={k} className="flex justify-between"><span className="capitalize">{k} leads</span><span className="tabular-nums">{leads.find((l) => l.kind === k)?.n ?? 0}</span></li>)}
              <li className="flex justify-between border-t border-line pt-2"><span>Fake-door clicks (employer)</span><span className="tabular-nums">{doors}</span></li>
            </ul>
          </Panel>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Waitlist by jurisdiction (expansion evidence)">
            {waitlist.length === 0 ? <p className="text-sm text-muted">No waitlist sign-ups yet.</p> : <BarList rows={waitlist.map((w) => ({ label: JURISDICTIONS.find((j) => j.code === w.jurisdiction)?.name ?? w.jurisdiction, value: w.n, note: w.fsas ? `Areas: ${w.fsas}` : undefined }))} />}
          </Panel>
          <Panel title="Coaching capacity from workload">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted"><tr><th className="pb-1 font-medium">Plan</th><th className="pb-1 text-right font-medium">Active</th><th className="pb-1 text-right font-medium">Coach hrs / month</th></tr></thead>
              <tbody>{capacity.map((c) => <tr key={c.plan} className="border-t border-line"><td className="py-1">{c.plan}</td><td className="text-right tabular-nums">{c.members}</td><td className="text-right tabular-nums">{(c.minutes / 60).toFixed(1)}</td></tr>)}</tbody>
            </table>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <Stat label="Workload" value={`${(totalMin / 60).toFixed(1)} h`} sub="per month, live + async + onboarding" />
              <Stat label="Coach FTE needed" value={(totalMin / COACH_PRODUCTIVE_MIN_PER_FTE_MONTH).toFixed(2)} sub="at 110 productive h/FTE/month (assumption)" />
            </div>
          </Panel>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Panel title={<span className="flex items-center gap-2">Platform revenue <EntityTag entity="platform" /></span>}>
            <Stat label="Net of tax (paid orders)" value={cadExact(platformRev.net)} sub={`${platformRev.n} orders · HST collected ${cadExact(platformRev.tax)} · refunds ${cadExact(refunds.c)}`} />
            <p className="mt-3 text-xs text-muted">Includes seeded demo orders. Memberships and add-ons only.</p>
          </Panel>
          <Panel title={<span className="flex items-center gap-2">Pharmacy (reported) <EntityTag entity="pharmacy" /></span>}>
            <Stat label="Patient-paid fills" value={cadExact(pharm.patient_paid_cents)} sub={`${pharm.orders} orders — pharmacy revenue, not RECLAIM revenue`} />
            <p className="mt-3 text-xs text-muted">Aggregate reported by the pharmacy entity. RECLAIM&apos;s income from the pharmacy is a fixed technology fee, never a share of this.</p>
          </Panel>
          <Panel title={<span className="flex items-center gap-2">Medical practice <EntityTag entity="clinical" /></span>}>
            <p className="text-sm text-ink-2">Not visible to RECLAIM. Insured services are billed to OHIP by the practice; the practice pays RECLAIM a fixed services fee.</p>
          </Panel>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Panel title="Email outbox (prototype — nothing is sent)">
            <ul className="divide-y divide-line text-sm">{outbox.map((o, i) => <li key={i} className="flex justify-between gap-4 py-2"><span><span className="font-medium">{o.subject}</span><span className="block text-xs text-muted">{o.to_email} · {o.class} · from {o.entity_id}</span></span><span className="shrink-0 text-xs text-muted">{fmtDateTime(o.created_at)}</span></li>)}</ul>
            {outbox.length === 0 && <p className="text-sm text-muted">Empty.</p>}
          </Panel>
          <Panel title="Governance">
            <ul className="space-y-2 text-sm">
              <li className="flex justify-between"><span>Platform audit chain</span><span className={chainBreak == null ? "text-series" : "text-ember"}>{chainBreak == null ? "intact" : `broken at #${chainBreak}`}</span></li>
              <li className="flex justify-between"><span>Open privacy requests</span><span className="tabular-nums">{openRequests}</span></li>
            </ul>
            <p className="mt-3 text-xs text-muted">Clinical and pharmacy audit chains are verified by those entities, not by founders.</p>
          </Panel>
        </div>
      </main>
    </div>
  );
}
