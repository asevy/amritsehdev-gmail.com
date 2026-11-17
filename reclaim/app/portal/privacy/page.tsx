import { requireUser } from "@/lib/auth";
import { currentConsents, consentHistory } from "@/lib/consent";
import { getEnrolment, accessLog } from "@/lib/clinical";
import { setConsent, requestDataAction } from "@/app/actions/portal";
import { CONSENTS, type ConsentKind } from "@/config/consents";
import { PageHeader, Panel, Flash } from "@/components/portal";
import { EntityTag } from "@/components/ui";
import { fmtDateTime } from "@/lib/money";

export default async function PrivacyPage({ searchParams }: { searchParams: Promise<{ requested?: string }> }) {
  const user = await requireUser(["member"]);
  const sp = await searchParams;
  const state = currentConsents(user.id);
  const history = consentHistory(user.id);
  const enrolled = !!getEnrolment(user);
  const log = enrolled ? accessLog(user) : [];
  const kinds = (Object.keys(CONSENTS) as ConsentKind[]).filter((k) => CONSENTS[k].withdrawable && (k !== "employer_aggregate" || user.sponsor_code));

  return (
    <>
      <PageHeader eyebrow="Privacy & data" title="You decide who sees what">
        Every choice here is separate, can be changed any time, and is recorded with the exact wording you agreed to.
      </PageHeader>
      {sp.requested && <Flash>Request received. We&apos;ll respond within 30 days.</Flash>}

      <Panel title="Your choices">
        <ul className="divide-y divide-line">
          {kinds.map((k) => {
            const def = CONSENTS[k];
            const on = state[k];
            return (
              <li key={k} className="flex flex-wrap items-start justify-between gap-4 py-4">
                <div className="max-w-xl">
                  <p className="flex items-center gap-2 font-medium">{def.label} <EntityTag entity={def.entity} /></p>
                  <p className="mt-1 text-sm leading-6 text-ink-2">{def.text}</p>
                </div>
                <form action={setConsent}>
                  <input type="hidden" name="kind" value={k} />
                  <input type="hidden" name="granted" value={on ? "0" : "1"} />
                  <button role="switch" aria-checked={on} aria-label={def.label} className={`relative h-7 w-12 rounded-full transition-colors ${on ? "bg-series" : "bg-line-2"}`}>
                    <span className={`absolute top-1 size-5 rounded-full bg-white shadow transition-all ${on ? "left-6" : "left-1"}`} />
                  </button>
                </form>
              </li>
            );
          })}
        </ul>
      </Panel>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Panel title="Your data">
          <div className="space-y-3 text-sm">
            <a href="/api/export" className="btn-primary btn-sm">Download my RECLAIM data (JSON)</a>
            <p className="text-ink-2">Includes account, Blueprint versions, measurements, plan, video progress, bookings, coach messages, orders and consent history. {enrolled && "A summary of your medical-practice record is included, labelled separately."}</p>
            <div className="flex flex-wrap gap-2 pt-2">
              <form action={requestDataAction}><input type="hidden" name="kind" value="correction" /><input type="hidden" name="entity" value="platform" /><button className="btn-ghost btn-sm">Request a correction</button></form>
              <form action={requestDataAction}><input type="hidden" name="kind" value="deletion" /><input type="hidden" name="entity" value="platform" /><button className="btn-danger btn-sm">Request deletion</button></form>
              {enrolled && <form action={requestDataAction}><input type="hidden" name="kind" value="access" /><input type="hidden" name="entity" value="clinical" /><button className="btn-ghost btn-sm">Full copy of medical record (to the practice)</button></form>}
            </div>
            <p className="text-xs text-muted">Deletion removes RECLAIM data except records we must keep (financial records for tax, proof of consent). Medical records are kept by the practice as required by law; you can ask it to correct them.</p>
          </div>
        </Panel>
        <Panel title={<span className="flex items-center gap-2">Who accessed your medical record <EntityTag entity="clinical" /></span>}>
          {!enrolled ? <p className="text-sm text-muted">You don&apos;t have a medical-practice record.</p> : log.length === 0 ? <p className="text-sm text-muted">No access by anyone other than you.</p> : (
            <ul className="space-y-1.5 text-sm">{log.map((l, i) => <li key={i} className="flex justify-between gap-4"><span>{l.actor_role} · {l.action}</span><span className="text-muted">{fmtDateTime(l.created_at)}</span></li>)}</ul>
          )}
          <p className="mt-3 text-xs text-muted">RECLAIM founders and coaches have no access to medical records. Each entry is hash-chained so it can&apos;t be silently altered.</p>
        </Panel>
      </div>

      <Panel title="Consent history" className="mt-5">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted"><tr><th className="pb-2 font-medium">When</th><th className="pb-2 font-medium">Choice</th><th className="pb-2 font-medium">Decision</th><th className="pb-2 font-medium">Wording fingerprint</th></tr></thead>
          <tbody className="divide-y divide-line">{history.map((h, i) => <tr key={i}><td className="py-1.5">{fmtDateTime(h.created_at)}</td><td>{CONSENTS[h.kind]?.label ?? h.kind}</td><td>{h.granted ? "Granted" : "Declined / withdrawn"}</td><td className="font-mono text-xs text-muted">{h.text_sha.slice(0, 10)} · {h.version}</td></tr>)}</tbody>
        </table>
      </Panel>
    </>
  );
}
