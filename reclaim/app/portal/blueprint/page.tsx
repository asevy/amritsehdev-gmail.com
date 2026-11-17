import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { latestBlueprint, blueprintVersions } from "@/lib/portal-data";
import { updateBlueprintPreferences } from "@/app/actions/portal";
import { PageHeader, Panel, MembershipRequired, Flash } from "@/components/portal";
import { fmtDate } from "@/lib/money";
import { GOAL_OPTIONS, BARRIER_OPTIONS } from "@/lib/assessment";

type BP = {
  goals?: string[]; capacity?: Record<string, unknown>; painLimitations?: string; nutrition?: { pattern?: string; cookingTime?: string; notes?: string };
  preferences?: { setting?: string[]; enjoys?: string }; schedule?: { daysPerWeek?: number; minutesPerSession?: number; bestTimes?: string };
  sleep?: { hours?: number; notes?: string }; barriers?: string[]; coaching?: { style?: string; contact?: string };
  targets?: { label: string; baseline: number; target: number; by: string }[]; fromAssessment?: Record<string, unknown>;
};

const label = (opts: { id: string; label: string }[], id: string) => opts.find((o) => o.id === id)?.label ?? id;

export default async function BlueprintPage({ searchParams }: { searchParams: Promise<{ saved?: string }> }) {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const { saved } = await searchParams;
  const bp = latestBlueprint(user.id);
  const data: BP = bp ? JSON.parse(bp.data_json) : {};
  const versions = blueprintVersions(user.id);
  const fa = data.fromAssessment as (BP & { daysPerWeek?: number; minutesPerSession?: number; sleepHours?: number; coachingStyle?: string }) | undefined;

  return (
    <>
      <PageHeader eyebrow={bp ? `Version ${bp.version} · ${bp.author} · ${fmtDate(bp.created_at)}` : "Not built yet"} title="Your Blueprint">
        The written plan behind everything else: what you&apos;re aiming for, what you&apos;re working with, and how your week is set up. Every change creates a new version.
      </PageHeader>
      {saved && <Flash>Saved as a new version. Your coach will see it before your next plan update.</Flash>}
      {fa && !data.targets && (
        <div className="mb-6"><Flash>Built from your free assessment. Your coach will complete it — and set targets — in your Blueprint session.</Flash></div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Goals">
          <ul className="space-y-1.5 text-sm">{(data.goals ?? fa?.goals ?? []).map((g) => <li key={g}>• {label(GOAL_OPTIONS, g)}</li>)}</ul>
        </Panel>
        <Panel title="Measurable targets">
          {data.targets?.length ? (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted"><tr><th className="pb-2 font-medium">Measure</th><th className="pb-2 font-medium">Baseline</th><th className="pb-2 font-medium">Target</th><th className="pb-2 font-medium">By</th></tr></thead>
              <tbody className="divide-y divide-line">{data.targets.map((t) => <tr key={t.label}><td className="py-2">{t.label}</td><td className="tabular-nums">{t.baseline.toLocaleString()}</td><td className="tabular-nums font-semibold">{t.target.toLocaleString()}</td><td className="text-muted">{t.by}</td></tr>)}</tbody>
            </table>
          ) : <p className="text-sm text-muted">Set with your coach in the Blueprint session.</p>}
        </Panel>
        <Panel title="Physical capacity & pain">
          <dl className="space-y-2 text-sm">
            {data.capacity && Object.entries(data.capacity).map(([k, v]) => <div key={k} className="flex justify-between gap-4"><dt className="text-muted">{k.replace(/([A-Z])/g, " $1").toLowerCase()}</dt><dd>{String(v)}</dd></div>)}
            <div><dt className="text-muted">Pain limitations</dt><dd className="mt-0.5">{data.painLimitations || "None noted"}</dd></div>
          </dl>
        </Panel>
        <Panel title="Barriers & coaching">
          <p className="text-sm">{(data.barriers ?? fa?.barriers ?? []).map((b) => label(BARRIER_OPTIONS, b)).join(" · ") || "—"}</p>
          <p className="mt-3 text-sm text-ink-2">Preferred contact: {data.coaching?.contact ?? fa?.coachingStyle ?? "—"}</p>
          <p className="mt-1 text-sm text-ink-2">Sleep: {data.sleep?.hours ?? fa?.sleepHours ?? "—"} h {data.sleep?.notes ? `· ${data.sleep.notes}` : ""}</p>
          <p className="mt-1 text-sm text-ink-2">Nutrition: {[data.nutrition?.pattern, data.nutrition?.notes].filter(Boolean).join(" · ") || "—"}</p>
        </Panel>
      </div>

      <Panel title="Update your preferences" className="mt-5">
        <form action={updateBlueprintPreferences} className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm"><span className="field-label">Days per week</span><input name="daysPerWeek" type="number" min={1} max={7} defaultValue={data.schedule?.daysPerWeek ?? fa?.daysPerWeek ?? 3} className="input" /></label>
          <label className="text-sm"><span className="field-label">Minutes per session</span><input name="minutesPerSession" type="number" min={10} max={120} step={5} defaultValue={data.schedule?.minutesPerSession ?? fa?.minutesPerSession ?? 30} className="input" /></label>
          <label className="text-sm sm:col-span-2"><span className="field-label">Best times to train</span><input name="bestTimes" defaultValue={data.schedule?.bestTimes ?? ""} className="input" /></label>
          <label className="text-sm sm:col-span-2"><span className="field-label">Pain or movement limitations (in your words)</span><textarea name="painLimitations" rows={2} defaultValue={data.painLimitations ?? ""} className="input" /><span className="field-hint">For coaching only. Symptoms or medical questions belong in Care → Messages.</span></label>
          <label className="text-sm"><span className="field-label">Food notes</span><input name="nutritionNotes" defaultValue={data.nutrition?.notes ?? ""} className="input" /></label>
          <label className="text-sm"><span className="field-label">How you like to be coached</span><input name="coachingContact" defaultValue={data.coaching?.contact ?? ""} className="input" /></label>
          <div className="sm:col-span-2"><button className="btn-primary">Save as new version</button></div>
        </form>
      </Panel>

      <Panel title="Version history" className="mt-5">
        <ol className="space-y-2 text-sm">
          {versions.map((v) => <li key={v.version} className="flex justify-between gap-4"><span>v{v.version} · {v.author}</span><span className="text-muted">{fmtDate(v.created_at)} · {v.source}</span></li>)}
        </ol>
      </Panel>
    </>
  );
}
