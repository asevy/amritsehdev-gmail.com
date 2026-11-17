import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { hasConsent } from "@/lib/consent";
import { latestCareSummary } from "@/lib/clinical";
import { coachMessages, latestBlueprint } from "@/lib/portal-data";
import { coachReviewQueue, listForMember, getFormCheck, clipUrl, formScore } from "@/lib/form-checks";
import { coachReply } from "@/app/actions/staff";
import { submitReview } from "@/app/actions/form-checks";
import { FORM_EXERCISES, FORM_CHECK_LIMITS, RATING_LABEL, formExerciseById } from "@/config/exercises";
import { CONSENTS } from "@/config/consents";
import { METRICS } from "@/lib/mechanics";
import { FormCapture } from "@/components/FormCapture";
import { FormHistory } from "@/components/FormHistory";
import { Panel, Flash } from "@/components/portal";
import { Notice } from "@/components/ui";
import { fmtDate, fmtDateTime } from "@/lib/money";

export default async function CoachDesk({ searchParams }: { searchParams: Promise<{ m?: string; fc?: string; saved?: string; reviewed?: string; error?: string }> }) {
  const coach = await requireUser(["coach"]);
  const sp = await searchParams;
  const members = db("platform").prepare(
    `SELECT u.id, u.name, u.patient_ref, s.plan_id FROM users u JOIN subscriptions s ON s.user_id = u.id AND s.status <> 'cancelled' WHERE u.role = 'member' ORDER BY u.name`,
  ).all() as Array<{ id: string; name: string; patient_ref: string | null; plan_id: string }>;
  const queue = coachReviewQueue();
  const fc = sp.fc ? getFormCheck(sp.fc) : null;
  const selId = fc?.user_id ?? sp.m;
  const sel = members.find((x) => x.id === selId);
  const msgs = sel ? coachMessages(sel.id) : [];
  const bp = sel ? latestBlueprint(sel.id) : null;
  const summary = sel?.patient_ref && hasConsent(sel.id, "clinical_summary_to_coach") ? latestCareSummary(sel.patient_ref) : null;
  const history = sel ? listForMember(sel.id) : [];

  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <div className="space-y-5">
        <Panel title={`Form checks to review (${queue.length})`}>
          {queue.length === 0 ? <p className="text-sm text-muted">All caught up.</p> : (
            <ul className="space-y-1">{queue.map((q) => (
              <li key={q.id}><Link href={`/staff/coach?fc=${q.id}`} className={`block rounded-lg px-3 py-2 text-sm ${sp.fc === q.id ? "bg-ink text-paper" : "hover:bg-bone"}`}>
                {q.member_name} · {formExerciseById(q.exercise)?.name}<span className="block text-xs opacity-70">{fmtDateTime(q.created_at)}{q.file_path ? "" : " · measurements only"}</span>
              </Link></li>
            ))}</ul>
          )}
        </Panel>
        <Panel title={`Caseload (${members.length})`}>
          <ul className="space-y-1">{members.map((x) => (
            <li key={x.id}><Link href={`/staff/coach?m=${x.id}`} className={`block rounded-lg px-3 py-2 text-sm ${selId === x.id && !sp.fc ? "bg-ink text-paper" : "hover:bg-bone"}`}>{x.name}<span className="block text-xs opacity-70">{x.plan_id}</span></Link></li>
          ))}</ul>
        </Panel>
      </div>

      {!sel ? <Notice>Select a member or a form check. Coaches see coaching data and form checks only; medical records are never shown here.</Notice> : (
        <div className="space-y-5">
          {sp.saved && <Flash>Saved to {sel.name}&apos;s programme. It appears in their form checks and record.</Flash>}
          {sp.reviewed && <Flash>Review sent. {sel.name} sees your cues on their Today page and in their record.</Flash>}
          {sp.error && <Flash tone="err">{sp.error}</Flash>}
          <h1 className="text-3xl font-medium">{sel.name}</h1>

          {fc && fc.status === "submitted" && (() => {
            const ex = formExerciseById(fc.exercise)!;
            const url = clipUrl(coach.id, fc);
            return (
              <Panel title={`Review: ${ex.name} · ${fmtDateTime(fc.created_at)}`}>
                <div className="grid gap-5 lg:grid-cols-2">
                  <div>
                    {url ? <video src={url} controls muted playsInline className="aspect-video w-full rounded-xl bg-ink object-contain" aria-label={`${sel.name} ${ex.name}`} /> : <p className="rounded-xl bg-bone p-4 text-sm">Member shared measurements only — no video.</p>}
                    {fc.member_note && <p className="mt-2 text-sm"><span className="text-muted">Member note:</span> {fc.member_note}</p>}
                    <dl className="mt-3 divide-y divide-line text-sm">
                      {METRICS[fc.exercise].map((m) => <div key={m.key} className="flex justify-between py-1"><dt className="text-ink-2">{m.label} (est.)</dt><dd className="tabular-nums">{fc.mechanics?.metrics[m.key] != null ? `${fc.mechanics.metrics[m.key]}${m.unit}` : "—"}</dd></div>)}
                    </dl>
                    {fc.mechanics?.quality === "low" && <p className="mt-2 text-xs text-warn">Low-confidence measurement: {fc.mechanics.notes.join(" ")}</p>}
                  </div>
                  <form action={submitReview} className="space-y-4">
                    <input type="hidden" name="id" value={fc.id} />
                    {ex.criteria.map((c) => (
                      <fieldset key={c.id}>
                        <legend className="text-sm font-medium">{c.label}</legend>
                        <div className="mt-1 flex gap-2">
                          {[1, 2, 3].map((v) => (
                            <label key={v} className="flex cursor-pointer items-center gap-1.5 rounded-full border border-line-2 px-3 py-1 text-sm has-checked:border-ink has-checked:bg-ink has-checked:text-paper">
                              <input type="radio" name={`score_${c.id}`} value={v} required className="sr-only" />{RATING_LABEL[v]}
                            </label>
                          ))}
                        </div>
                      </fieldset>
                    ))}
                    <label className="block text-sm"><span className="field-label">Cues for the member</span><textarea name="cues" rows={4} required className="input" placeholder="One or two things to focus on next time" /></label>
                    <button className="btn-primary">Send review</button>
                    <p className="text-xs text-muted">Pain, swelling or other symptoms → direct the member to Care (medical practice), not a cue.</p>
                  </form>
                </div>
              </Panel>
            );
          })()}

          <Panel title={`Record a form check with ${sel.name.split(" ")[0]}`}>
            <p className="mb-4 text-sm text-ink-2">In a session, film the lift here or upload it from your phone. It&apos;s saved straight into {sel.name.split(" ")[0]}&apos;s programme and doesn&apos;t use their monthly allowance.</p>
            <FormCapture mode="coach" memberId={sel.id} memberName={sel.name.split(" ")[0]} exercises={FORM_EXERCISES.map(({ id, name, filming }) => ({ id, name, filming }))} needsConsent={false} consentText={CONSENTS.form_check_video.text} maxSeconds={FORM_CHECK_LIMITS.maxSeconds} />
          </Panel>

          {history.length > 0 && (
            <div className="space-y-4">
              <h2 className="font-sans text-lg font-semibold tracking-normal">Form history {history.filter((c) => c.scores).length > 0 && <span className="text-sm font-normal text-muted">· latest form score {formScore([...history].reverse().find((c) => c.scores)!)}%</span>}</h2>
              {FORM_EXERCISES.map((e) => <FormHistory key={e.id} checks={history} exerciseId={e.id} viewerId={coach.id} compact />)}
            </div>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Care-team summary from clinician">
              {summary ? <p className="text-sm">{summary.coach_safe_text}</p> : <p className="text-sm text-muted">None shared (no summary, or the member hasn&apos;t turned sharing on).</p>}
            </Panel>
            <Panel title={`Blueprint v${bp?.version ?? "—"}`}>
              <pre className="max-h-48 overflow-auto rounded-lg bg-bone/60 p-3 text-xs">{bp ? JSON.stringify(JSON.parse(bp.data_json), null, 2) : "—"}</pre>
            </Panel>
          </div>
          <Panel title="Messages">
            <ol className="space-y-2 text-sm">{msgs.map((x) => <li key={x.id}><span className="text-xs text-muted">{x.sender_name} · {fmtDateTime(x.created_at)}</span><p>{x.body}</p></li>)}</ol>
            <form action={coachReply} className="mt-3 flex gap-2"><input type="hidden" name="memberId" value={sel.id} /><input name="body" className="input" placeholder="Reply" /><button className="btn-primary btn-sm shrink-0">Send</button></form>
            <p className="mt-2 text-xs text-muted">Symptoms, medication or results → direct the member to Care → Messages (medical practice). Last active {fmtDate(msgs.at(-1)?.created_at)}.</p>
          </Panel>
        </div>
      )}
    </div>
  );
}
