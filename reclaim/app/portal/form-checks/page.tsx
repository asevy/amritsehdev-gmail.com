import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { hasConsent } from "@/lib/consent";
import { listForMember, allowance, nextDue } from "@/lib/form-checks";
import { deleteFormCheckVideoAction } from "@/app/actions/form-checks";
import { FORM_EXERCISES, FORM_CHECK_LIMITS, formExerciseById } from "@/config/exercises";
import { CONSENTS } from "@/config/consents";
import { FormCapture } from "@/components/FormCapture";
import { FormHistory } from "@/components/FormHistory";
import { PageHeader, Panel, MembershipRequired, Flash } from "@/components/portal";
import { fmtDate } from "@/lib/money";

export default async function FormChecksPage({ searchParams }: { searchParams: Promise<{ saved?: string; deleted?: string; exercise?: string }> }) {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const sp = await searchParams;
  const checks = listForMember(user.id);
  const a = allowance(user.id);
  const left = Math.max(0, a.limit - a.used);
  const due = FORM_EXERCISES.map((e) => ({ e, d: nextDue(checks, e.id) })).filter((x) => x.d && x.d.getTime() <= Date.now());
  const notYet = FORM_EXERCISES.filter((e) => !checks.some((c) => c.exercise === e.id));

  return (
    <>
      <PageHeader eyebrow="Form checks" title="Your form, over time" actions={<div className="card px-5 py-3 text-right"><p className="eyebrow">Reviews left this month</p><p className="text-3xl font-semibold">{left}<span className="text-base font-normal text-muted"> of {a.limit}</span></p></div>}>
        Film a lift; the phone measures it; your coach rates it and sends cues. Every check is saved here, so you can see how your technique changes.
      </PageHeader>
      {sp.saved && <Flash>Saved to your programme. Your coach reviews it within 2 business days.</Flash>}
      {sp.deleted && <Flash>Deleted.</Flash>}
      {due.length > 0 && <Flash tone="err">Re-film due: {due.map((x) => x.e.name).join(", ")} — it&apos;s been 4 weeks.</Flash>}

      <Panel title="New form check" className="mb-6">
        <FormCapture
          mode="member"
          exercises={FORM_EXERCISES.map(({ id, name, filming }) => ({ id, name, filming }))}
          defaultExercise={formExerciseById(sp.exercise ?? "")?.id ?? due[0]?.e.id ?? notYet[0]?.id}
          needsConsent={!hasConsent(user.id, "form_check_video")}
          consentText={CONSENTS.form_check_video.text}
          maxSeconds={FORM_CHECK_LIMITS.maxSeconds}
          allowanceNote={left === 0 ? "monthly reviews used — your coach can record one with you in a session" : undefined}
          disabled={left === 0}
        />
      </Panel>

      <div className="space-y-5">
        {FORM_EXERCISES.map((e) => <FormHistory key={e.id} checks={checks} exerciseId={e.id} viewerId={user.id} deleteAction={deleteFormCheckVideoAction} />)}
      </div>
      {notYet.length > 0 && <p className="mt-5 text-sm text-muted">Not filmed yet: {notYet.map((e) => e.name).join(", ")}.</p>}
      {checks.length > 0 && <p className="mt-2 text-xs text-muted">First check {fmtDate(checks[0].created_at)}. Videos are visible only to you and your coach and can be deleted any time; measurements are estimates from one camera angle.</p>}
    </>
  );
}
