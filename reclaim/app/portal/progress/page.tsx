import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { measurements, METRIC_META, latestBlueprint } from "@/lib/portal-data";
import { logMeasurement } from "@/app/actions/portal";
import { LineChart } from "@/components/charts";
import { PageHeader, Panel, MembershipRequired, Flash } from "@/components/portal";
import { fmtDate } from "@/lib/money";

const ORDER = ["sit_to_stand", "waist_cm", "steps", "weight_kg", "sleep_h", "lean_mass_kg", "body_fat_pct"];

export default async function ProgressPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const { error } = await searchParams;
  const ms = measurements(user.id);
  const bp = latestBlueprint(user.id);
  const targets = new Map<string, number>((bp ? JSON.parse(bp.data_json).targets ?? [] : []).map((t: { metric: string; target: number }) => [t.metric, t.target]));
  const metrics = ORDER.filter((m) => ms.some((x) => x.metric === m));

  return (
    <>
      <PageHeader eyebrow="Progress" title="What's changing">
        Strength and waist first; the scale is one signal among several. Scans from partner facilities appear here automatically.
      </PageHeader>
      {error && <Flash tone="err">That value looks out of range — please check and try again.</Flash>}

      <Panel title="Log a measurement" className="mb-5">
        <form action={logMeasurement} className="flex flex-wrap items-end gap-3">
          <label className="text-sm"><span className="field-label">Measure</span>
            <select name="metric" className="input">
              {["sit_to_stand", "waist_cm", "weight_kg", "steps", "sleep_h"].map((m) => <option key={m} value={m}>{METRIC_META[m].label}</option>)}
            </select>
          </label>
          <label className="text-sm"><span className="field-label">Value</span><input name="value" type="number" step="any" required className="input w-32" /></label>
          <label className="text-sm"><span className="field-label">Note (optional)</span><input name="note" className="input w-56" /></label>
          <button className="btn-primary">Save</button>
        </form>
      </Panel>

      <div className="grid gap-5 lg:grid-cols-2">
        {metrics.map((m) => {
          const meta = METRIC_META[m];
          const pts = ms.filter((x) => x.metric === m).map((x) => ({ t: x.measured_at, v: x.value }));
          const first = pts[0]?.v, last = pts.at(-1)?.v;
          const delta = first != null && last != null ? last - first : 0;
          return (
            <Panel key={m} title={meta.label} action={<span className="text-xs text-muted">{pts.length} readings · {ms.find((x) => x.metric === m)?.source === "partner_scan" ? "partner scan" : "self/coach"}</span>}>
              <p className="mb-2 text-sm text-ink-2">
                {delta === 0 ? "No change yet" : `${delta > 0 ? "+" : ""}${delta.toLocaleString("en-CA", { maximumFractionDigits: meta.decimals })} ${meta.unit} since ${fmtDate(pts[0].t)}`}
              </p>
              <LineChart points={pts} unit={meta.unit} target={targets.get(m) ?? null} decimals={meta.decimals} ariaLabel={`${meta.label} over time`} />
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer text-xs text-muted">Show data table</summary>
                <table className="mt-2 w-full text-xs">
                  <thead className="text-left text-muted"><tr><th className="py-1 font-medium">Date</th><th className="py-1 text-right font-medium">Value ({meta.unit})</th></tr></thead>
                  <tbody>{pts.map((p) => <tr key={p.t} className="border-t border-line"><td className="py-1">{fmtDate(p.t)}</td><td className="py-1 text-right tabular-nums">{p.v.toLocaleString("en-CA")}</td></tr>)}</tbody>
                </table>
              </details>
            </Panel>
          );
        })}
      </div>
      <p className="mt-6 text-xs text-muted">Demo account data is fictional. Measurements are for coaching; they are not medical tests and aren&apos;t sent to the medical practice unless you turn on sharing in Privacy.</p>
    </>
  );
}
