import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { clinicianQueue, clinicianChart } from "@/lib/clinical";
import { signEncounter, prescribe, clinicianMessage, writeCareSummary } from "@/app/actions/staff";
import { Panel, Flash } from "@/components/portal";
import { Notice } from "@/components/ui";
import { fmtDate, fmtDateTime } from "@/lib/money";

export default async function ClinicianDesk({ searchParams }: { searchParams: Promise<{ p?: string; rx?: string; error?: string }> }) {
  const user = await requireUser(["clinician"]);
  const sp = await searchParams;
  const queue = clinicianQueue(user);
  const chart = sp.p ? clinicianChart(user, sp.p) : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
      <Panel title="Patients">
        <ul className="space-y-1">
          {queue.map((q) => {
            const flags = q.flags ? (JSON.parse(q.flags) as { urgent: string[]; review: string[] }) : { urgent: [], review: [] };
            return (
              <li key={q.patient_ref}>
                <Link href={`/staff/clinician?p=${q.patient_ref}`} className={`block rounded-lg px-3 py-2 text-sm ${sp.p === q.patient_ref ? "bg-ink text-paper" : "hover:bg-bone"}`}>
                  <span className="font-medium">{q.legal_name}</span>
                  <span className="block text-xs opacity-70">{q.enrolment.replace("_", " ")} · next {q.next_visit ? fmtDate(q.next_visit) : "—"}</span>
                  {(flags.urgent.length > 0 || flags.review.length > 0 || q.new_reports > 0 || q.unanswered > 0) && (
                    <span className="mt-1 flex flex-wrap gap-1 text-[10px] uppercase tracking-wide">
                      {flags.urgent.length > 0 && <span className="rounded bg-ember px-1.5 text-white">urgent</span>}
                      {flags.review.length > 0 && <span className="rounded bg-warn-soft px-1.5 text-warn">review</span>}
                      {q.new_reports > 0 && <span className="rounded bg-ember-soft px-1.5 text-ember">side effect</span>}
                      {q.unanswered > 0 && <span className="rounded bg-clinic-soft px-1.5 text-clinic">message</span>}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
        <p className="mt-4 text-xs text-muted">Every chart view is written to the practice&apos;s audit log and shown to the patient.</p>
      </Panel>

      {!chart?.patient ? (
        <Notice tone="clinical" title="Independent clinical workspace">
          This desk belongs to the medical practice. It shows no revenue, conversion or pharmacy-choice data, and nothing here is visible to RECLAIM founders or coaches. In production this is the practice&apos;s certified EMR.
        </Notice>
      ) : (
        <div className="space-y-5">
          {sp.rx && <Flash>Prescription issued. The patient chooses the pharmacy in their portal.</Flash>}
          {sp.error && <Flash tone="err">{sp.error}</Flash>}
          <div>
            <h1 className="text-3xl font-medium">{chart.patient.legal_name}</h1>
            <p className="text-sm text-muted">DOB {chart.patient.dob} · {chart.patient.province} · Health card {chart.patient.hcn_masked ?? "not provided"}</p>
          </div>
          {chart.intake && (
            <Panel title={`Intake · ${fmtDate(chart.intake.submitted_at)}`}>
              {(() => {
                const f = JSON.parse(chart.intake.red_flags_json) as { urgent: string[]; review: string[] };
                return f.urgent.length + f.review.length > 0 ? (
                  <ul className="mb-3 space-y-1 text-sm">{[...f.urgent.map((x) => `URGENT: ${x}`), ...f.review.map((x) => `Review: ${x}`)].map((x) => <li key={x} className="text-ember">• {x}</li>)}</ul>
                ) : <p className="mb-3 text-sm text-moss">No red flags from intake rules.</p>;
              })()}
              <pre className="max-h-48 overflow-auto rounded-lg bg-bone/60 p-3 text-xs">{JSON.stringify(JSON.parse(chart.intake.answers_json), null, 2)}</pre>
            </Panel>
          )}
          <Panel title="Encounters">
            <ul className="space-y-3 text-sm">{chart.encounters.map((e) => (
              <li key={e.id} className="rounded-lg border border-line p-3">
                <p className="font-medium">{e.kind} · {fmtDateTime(e.starts_at)} · {e.status} · {e.insured_status === "ohip" ? "OHIP-insured ($0 to patient)" : e.insured_status}</p>
                {e.note && <p className="mt-1 text-ink-2">{e.note}</p>}
                {e.status === "booked" && (
                  <form action={signEncounter} className="mt-2 flex gap-2"><input type="hidden" name="encounterId" value={e.id} /><input name="note" className="input" placeholder="Visit note (demo)" required /><button className="btn-primary btn-sm shrink-0">Complete & sign</button></form>
                )}
              </li>
            ))}</ul>
          </Panel>
          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Prescribe from formulary">
              <form action={prescribe} className="space-y-3 text-sm">
                <input type="hidden" name="patientRef" value={sp.p} />
                <select name="formularyId" className="input" required>{chart.formulary.map((f) => <option key={f.id} value={f.id}>{f.display_name}</option>)}</select>
                <input name="sig" className="input" placeholder="Directions" />
                <div className="flex gap-2"><input name="quantity" className="input" placeholder="Quantity" /><input name="refills" type="number" min={0} max={11} defaultValue={0} className="input w-24" aria-label="Refills" /></div>
                <button className="btn-primary btn-sm">Issue prescription</button>
                <p className="text-xs text-muted">Only Health Canada-authorised products approved by clinical governance appear here. One product per prescription. No incentive is attached to prescribing or to where it&apos;s filled.</p>
              </form>
              <ul className="mt-4 space-y-1 text-xs text-ink-2">{chart.prescriptions.map((p) => <li key={p.id}>{fmtDate(p.created_at)} · {p.display_name} · {p.status}</li>)}</ul>
            </Panel>
            <Panel title="Care-team summary for coach">
              <p className="text-xs text-muted">Shared with the coach only while the patient&apos;s consent is on. No diagnoses, results or medication details.</p>
              {chart.summary && <p className="mt-2 rounded-lg bg-bone/60 p-3 text-sm">{chart.summary.coach_safe_text}</p>}
              <form action={writeCareSummary} className="mt-3 space-y-2"><input type="hidden" name="patientRef" value={sp.p} /><textarea name="text" rows={2} className="input" placeholder="e.g. Cleared for progressive strength training." /><button className="btn-ghost btn-sm">Update summary</button></form>
            </Panel>
          </div>
          <Panel title="Messages & side-effect reports">
            {chart.reports.map((r) => <p key={r.id} className="mb-2 rounded-lg bg-ember-soft/60 p-2 text-sm"><strong className="capitalize">{r.severity}</strong> · {r.description} <span className="text-xs text-muted">({r.status}, {fmtDate(r.created_at)})</span></p>)}
            <ol className="space-y-2 text-sm">{chart.messages.map((m, i) => <li key={i}><span className="text-xs text-muted">{m.sender_name} · {fmtDateTime(m.created_at)}</span><p>{m.body}</p></li>)}</ol>
            <form action={clinicianMessage} className="mt-3 flex gap-2"><input type="hidden" name="patientRef" value={sp.p} /><input name="body" className="input" placeholder="Reply to patient" /><button className="btn-primary btn-sm shrink-0">Send</button></form>
          </Panel>
        </div>
      )}
    </div>
  );
}
