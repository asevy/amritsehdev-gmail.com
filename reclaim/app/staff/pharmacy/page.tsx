import { requireUser } from "@/lib/auth";
import { pharmacistQueue } from "@/lib/pharmacy";
import { verifyFill, shipFill } from "@/app/actions/staff";
import { Panel, Flash } from "@/components/portal";
import { Notice } from "@/components/ui";
import { cadExact, fmtDateTime } from "@/lib/money";

export default async function PharmacyDesk({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const user = await requireUser(["pharmacist"]);
  const { error } = await searchParams;
  const queue = pharmacistQueue(user);
  return (
    <>
      <h1 className="text-3xl font-medium">Fill queue</h1>
      <p className="mt-1 text-sm text-ink-2">Only prescriptions patients chose to send to this pharmacy appear here. Prices come from the pharmacy&apos;s price list and depend only on product, quantity and drug-plan coverage.</p>
      {error && <div className="mt-4"><Flash tone="err">{error}</Flash></div>}
      <div className="mt-6 space-y-4">
        {queue.length === 0 && <Notice>No fills yet. Log in as the member, choose the partner pharmacy for the demo prescription, and request a fill.</Notice>}
        {queue.map((f) => (
          <Panel key={f.id} title={`${f.legal_name} · ${f.display_name}`} action={<span className="chip border-line-2 text-muted">{f.status.replace("_", " ")}</span>}>
            <p className="text-sm text-ink-2">{f.sig} · {f.quantity} · DIN {f.din} · requested {fmtDateTime(f.requested_at)}</p>
            {f.status === "requested" && (
              <form action={verifyFill} className="mt-3 flex flex-wrap items-end gap-3 rounded-xl bg-bone/60 p-3 text-sm">
                <input type="hidden" name="fillId" value={f.id} />
                <label className="flex items-center gap-2"><input type="checkbox" name="counselled" className="accent-ink" /> Pharmacist counselling completed (required for first fill)</label>
                <label><span className="field-label">Drug plan pays (%)</span><input name="planPaysPct" type="number" min={0} max={100} defaultValue={0} className="input w-24" /></label>
                <button className="btn-primary btn-sm">Verify & price</button>
              </form>
            )}
            {f.patient_total_cents != null && <p className="mt-2 text-sm">Patient pays: <strong>{cadExact(f.patient_total_cents)}</strong> (plan {cadExact(f.plan_pays_cents)}) · {f.insurance_status}</p>}
            {f.status === "paid" && <form action={shipFill} className="mt-3"><input type="hidden" name="fillId" value={f.id} /><button className="btn-primary btn-sm">Mark shipped (cold chain)</button></form>}
            {f.tracking && <p className="mt-2 text-xs text-muted">Tracking {f.tracking}</p>}
          </Panel>
        ))}
      </div>
    </>
  );
}
