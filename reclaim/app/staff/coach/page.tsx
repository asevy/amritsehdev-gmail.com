import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { hasConsent } from "@/lib/consent";
import { latestCareSummary } from "@/lib/clinical";
import { coachMessages, latestBlueprint } from "@/lib/portal-data";
import { coachReply } from "@/app/actions/staff";
import { Panel } from "@/components/portal";
import { Notice } from "@/components/ui";
import { fmtDateTime } from "@/lib/money";

export default async function CoachDesk({ searchParams }: { searchParams: Promise<{ m?: string }> }) {
  await requireUser(["coach"]);
  const { m } = await searchParams;
  const members = db("platform").prepare(
    `SELECT u.id, u.name, u.patient_ref, s.plan_id FROM users u JOIN subscriptions s ON s.user_id = u.id AND s.status <> 'cancelled' WHERE u.role = 'member' ORDER BY u.name`,
  ).all() as Array<{ id: string; name: string; patient_ref: string | null; plan_id: string }>;
  const sel = members.find((x) => x.id === m);
  const msgs = sel ? coachMessages(sel.id) : [];
  const bp = sel ? latestBlueprint(sel.id) : null;
  const summary = sel?.patient_ref && hasConsent(sel.id, "clinical_summary_to_coach") ? latestCareSummary(sel.patient_ref) : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
      <Panel title={`Caseload (${members.length})`}>
        <ul className="space-y-1">{members.map((x) => (
          <li key={x.id}><Link href={`/staff/coach?m=${x.id}`} className={`block rounded-lg px-3 py-2 text-sm ${m === x.id ? "bg-ink text-paper" : "hover:bg-bone"}`}>{x.name}<span className="block text-xs opacity-70">{x.plan_id}</span></Link></li>
        ))}</ul>
      </Panel>
      {!sel ? <Notice>Select a member. Coaches see coaching data only; medical records are never shown here.</Notice> : (
        <div className="space-y-5">
          <h1 className="text-3xl font-medium">{sel.name}</h1>
          <Panel title="Care-team summary from clinician">
            {summary ? <p className="text-sm">{summary.coach_safe_text}</p> : <p className="text-sm text-muted">None shared (no summary, or the member hasn&apos;t turned sharing on).</p>}
          </Panel>
          <Panel title={`Blueprint v${bp?.version ?? "—"}`}>
            <pre className="max-h-48 overflow-auto rounded-lg bg-bone/60 p-3 text-xs">{bp ? JSON.stringify(JSON.parse(bp.data_json), null, 2) : "—"}</pre>
          </Panel>
          <Panel title="Messages">
            <ol className="space-y-2 text-sm">{msgs.map((x) => <li key={x.id}><span className="text-xs text-muted">{x.sender_name} · {fmtDateTime(x.created_at)}</span><p>{x.body}</p></li>)}</ol>
            <form action={coachReply} className="mt-3 flex gap-2"><input type="hidden" name="memberId" value={sel.id} /><input name="body" className="input" placeholder="Reply" /><button className="btn-primary btn-sm shrink-0">Send</button></form>
            <p className="mt-2 text-xs text-muted">Symptoms, medication or results → direct the member to Care → Messages (medical practice).</p>
          </Panel>
        </div>
      )}
    </div>
  );
}
