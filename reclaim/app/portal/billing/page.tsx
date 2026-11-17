import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription, refundEligibility } from "@/lib/commerce";
import { orders } from "@/lib/portal-data";
import { cancelMembership, pauseMembership, resumeMembership } from "@/app/actions/commerce";
import { planById, ADD_ONS } from "@/config/catalog";
import { ENTITIES } from "@/config/site";
import { PageHeader, Panel, Flash } from "@/components/portal";
import { EntityTag } from "@/components/ui";
import { cadExact, fmtDate } from "@/lib/money";

export default async function BillingPage({ searchParams }: { searchParams: Promise<{ cancelled?: string; paused?: string; step?: string }> }) {
  const user = await requireUser(["member"]);
  const sp = await searchParams;
  const sub = activeSubscription(user.id);
  const plan = sub ? planById(sub.plan_id) : null;
  const refund = refundEligibility(user.id);
  const list = orders(user.id);

  return (
    <>
      <PageHeader eyebrow={<EntityTag entity="platform" label={`Billed by ${ENTITIES.platform.displayName}`} />} title="Billing">
        Membership and add-ons only. Medication is billed by your pharmacy; any uninsured medical service by the medical practice.
      </PageHeader>
      {sp.cancelled && <Flash>Your membership is cancelled. A confirmation email is on its way.</Flash>}
      {sp.paused && <Flash>Paused. Nothing will be charged until the date shown.</Flash>}

      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <Panel title="Membership">
          {!sub || !plan ? (
            <div><p className="text-sm text-ink-2">No active membership.</p><Link href="/programmes" className="btn-primary btn-sm mt-3">Choose a programme</Link></div>
          ) : (
            <div>
              <p className="text-2xl font-semibold">{plan.name}</p>
              <p className="mt-1 text-sm text-ink-2">{sub.sponsored ? "Sponsored by your employer" : `${cadExact(sub.price_cents)} / month + HST`} · since {fmtDate(sub.started_at)}</p>
              <p className="mt-3 text-sm">
                {sub.status === "paused" ? <>Paused until <strong>{fmtDate(sub.paused_until)}</strong></> :
                  sub.cancel_at_period_end ? <>Ends on <strong>{fmtDate(sub.current_period_end)}</strong> — you won&apos;t be charged again</> :
                    <>Renews on <strong>{fmtDate(sub.current_period_end)}</strong></>}
              </p>

              {sub.cancel_at_period_end || sub.status === "paused" ? (
                <form action={resumeMembership} className="mt-5"><button className="btn-primary btn-sm">{sub.status === "paused" ? "Resume now" : "Keep my membership"}</button></form>
              ) : sp.step === "cancel" ? (
                <form action={cancelMembership} className="mt-5 space-y-3 rounded-xl border border-ember/30 bg-ember-soft/40 p-4">
                  <p className="font-semibold">Confirm cancellation</p>
                  <p className="text-sm text-ink-2">
                    {refund.eligible ? <>You&apos;re within 14 days of your first payment, so you&apos;ll get a full refund of {cadExact(refund.amountCents!)} and access ends now.</> : <>Your membership runs until {fmtDate(sub.current_period_end)}, then stops. No further charges.</>} Medical care and prescriptions are not affected.
                  </p>
                  <label className="block text-sm"><span className="field-label">Reason (optional — helps us improve)</span>
                    <select name="reason" className="input"><option value="unspecified">Prefer not to say</option><option value="price">Price</option><option value="time">No time</option><option value="results">Not seeing results</option><option value="coach">Coaching fit</option><option value="reached_goal">Reached my goal</option><option value="other">Other</option></select>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <button className="btn-danger">Cancel membership</button>
                    <Link href="/portal/billing" className="btn-ghost">Keep it</Link>
                  </div>
                </form>
              ) : (
                <div className="mt-5 flex flex-wrap gap-2">
                  <Link href="/portal/billing?step=cancel" className="btn-danger btn-sm">Cancel membership</Link>
                  <form action={pauseMembership}><button className="btn-ghost btn-sm">Pause for a month</button></form>
                  <Link href="/programmes" className="btn-ghost btn-sm">Change plan</Link>
                </div>
              )}
              <p className="mt-4 text-xs text-muted">Cancelling takes two clicks and never requires a call. {refund.eligible ? "Full refund available (within 14 days of first payment)." : ""}</p>
            </div>
          )}
        </Panel>

        <Panel title="Add-ons" className="scroll-mt-24" action={<span id="addons" />}>
          <ul className="space-y-3 text-sm">
            {ADD_ONS.map((a) => <li key={a.id} className="flex justify-between gap-4"><span>{a.name}<span className="block text-xs text-muted">{a.description}</span></span><span className="font-mono">{cadExact(a.priceCents)}</span></li>)}
          </ul>
          <p className="mt-3 text-xs text-muted">One-off add-on checkout reuses the order-review flow (not wired in this prototype).</p>
        </Panel>
      </div>

      <Panel title="Receipts & agreements" className="mt-5">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted"><tr><th className="pb-2 font-medium">Date</th><th className="pb-2 font-medium">Order</th><th className="pb-2 font-medium">Status</th><th className="pb-2 text-right font-medium">Total (incl. tax)</th><th className="pb-2 text-right font-medium">Agreement</th></tr></thead>
          <tbody className="divide-y divide-line">
            {list.map((o) => (
              <tr key={o.id}><td className="py-2">{fmtDate(o.paid_at ?? o.created_at)}</td><td className="font-mono text-xs">{o.id}</td><td>{o.status}</td><td className="text-right tabular-nums">{cadExact(o.total_cents)}</td><td className="text-right font-mono text-xs text-muted">{o.agreement_sha.slice(0, 10)}</td></tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-muted">Receipts show {ENTITIES.platform.legalName} and its HST number [to be added]. Coaching by non-regulated providers is generally not an eligible medical expense; ask your benefits provider.</p>
      </Panel>
    </>
  );
}
