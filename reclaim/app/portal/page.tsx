import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription, creditBalance } from "@/lib/commerce";
import { currentWeekItems, bookings, measurements, METRIC_META, DAY_NAMES, latestBlueprint } from "@/lib/portal-data";
import { progressFor } from "@/lib/media-auth";
import { videoById } from "@/lib/videos";
import { getEnrolment, listPrescriptions } from "@/lib/clinical";
import { togglePlanItem } from "@/app/actions/portal";
import { PageHeader, Panel } from "@/components/portal";
import { EntityTag } from "@/components/ui";
import { fmtDateTime } from "@/lib/money";

export default async function PortalHome() {
  const user = await requireUser(["member"]);
  const sub = activeSubscription(user.id);
  const enrol = getEnrolment(user);
  const rxNeedingChoice = enrol ? listPrescriptions(user).filter((r) => r.status === "active" && !r.destination_type) : [];

  if (!sub) {
    return (
      <>
        <PageHeader eyebrow="Free account" title={`Hello, ${user.name.split(" ")[0]}.`}>Your account gives you access to the independent medical practice and your privacy settings.</PageHeader>
        <div className="grid gap-4 md:grid-cols-2">
          <Panel title={<span className="flex items-center gap-2">Medical assessment <EntityTag entity="clinical" /></span>}>
            <p className="text-sm text-ink-2">{enrol ? `Status: ${enrol.status.replace("_", " ")}` : "Request an assessment from the independent practice. No membership needed."}</p>
            <Link href="/portal/care" className="btn-primary btn-sm mt-4">Go to Care</Link>
          </Panel>
          <Panel title="Add coaching">
            <p className="text-sm text-ink-2">A membership adds your Blueprint, a coach, weekly plan, progress tracking and the video library.</p>
            <Link href="/programmes" className="btn-ghost btn-sm mt-4">See programmes</Link>
          </Panel>
        </div>
      </>
    );
  }

  const items = currentWeekItems(user.id);
  const today = (new Date().getDay() + 6) % 7;
  const todays = items.filter((i) => i.day === today);
  const done = items.filter((i) => i.done_at).length;
  const upcoming = bookings(user.id).filter((b) => b.status === "booked" && Date.parse(b.starts_at) > Date.now()).slice(0, 3);
  const prog = progressFor(user.id);
  const resume = [...prog.values()].filter((p) => !p.completed_at && p.position_s > 2).sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0];
  const resumeVideo = resume ? videoById(resume.video_id) : null;
  const ms = measurements(user.id);
  const bp = latestBlueprint(user.id);
  const targets: Array<{ metric: string; label: string; baseline: number; target: number }> = bp ? JSON.parse(bp.data_json).targets ?? [] : [];

  return (
    <>
      <PageHeader eyebrow={new Date().toLocaleDateString("en-CA", { weekday: "long", month: "long", day: "numeric", timeZone: "America/Toronto" })} title={`Today, ${user.name.split(" ")[0]}`} />

      {rxNeedingChoice.length > 0 && (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-clinic/30 bg-clinic-soft/60 p-4">
          <div className="flex items-center gap-3 text-sm"><EntityTag entity="clinical" /> Your clinician issued a prescription. Choose where you&apos;d like to fill it.</div>
          <Link href="/portal/care#prescriptions" className="btn-primary btn-sm">Choose a pharmacy</Link>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <Panel title={`${DAY_NAMES[today]} — today's plan`} action={<Link href="/portal/plan" className="text-sm underline">Whole week ({done}/{items.length})</Link>}>
          {todays.length === 0 ? <p className="text-sm text-muted">Rest day. A walk counts.</p> : (
            <ul className="space-y-3">
              {todays.map((i) => (
                <li key={i.id} className="flex items-start gap-3">
                  <form action={togglePlanItem}>
                    <input type="hidden" name="id" value={i.id} />
                    <button aria-label={i.done_at ? `Mark ${i.title} not done` : `Mark ${i.title} done`} className={`mt-0.5 grid size-6 place-items-center rounded-md border ${i.done_at ? "border-series bg-series text-white" : "border-line-2 hover:border-ink"}`}>{i.done_at ? "✓" : ""}</button>
                  </form>
                  <div className="min-w-0">
                    <p className={`font-medium ${i.done_at ? "text-muted line-through" : ""}`}>{i.title}</p>
                    {i.detail && <p className="text-sm text-ink-2">{i.detail}</p>}
                    {i.video_id && <Link href={`/portal/library/${i.video_id}`} className="text-sm underline">Watch: {videoById(i.video_id)?.title}</Link>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <div className="space-y-5">
          <Panel title="Coming up">
            {upcoming.length === 0 ? <p className="text-sm text-muted">Nothing booked.</p> : (
              <ul className="space-y-2 text-sm">
                {upcoming.map((b) => <li key={b.id}><p className="font-medium">{b.title}</p><p className="text-muted">{fmtDateTime(b.starts_at)}</p></li>)}
              </ul>
            )}
            <p className="mt-3 text-xs text-muted">{creditBalance(user.id)} local-network credits available</p>
          </Panel>
          {resumeVideo && resume && (
            <Panel title="Continue watching">
              <Link href={`/portal/library/${resumeVideo.id}`} className="group block">
                <p className="font-medium group-hover:underline">{resumeVideo.title}</p>
                <div className="mt-2 h-1.5 rounded-full bg-line"><div className="h-1.5 rounded-full bg-series" style={{ width: `${(resume.position_s / resume.duration_s) * 100}%` }} /></div>
                <p className="mt-1 text-xs text-muted">Resume at {Math.floor(resume.position_s / 60)}:{String(Math.floor(resume.position_s % 60)).padStart(2, "0")}</p>
              </Link>
            </Panel>
          )}
        </div>
      </div>

      <Panel title="Blueprint targets" className="mt-5" action={<Link href="/portal/progress" className="text-sm underline">Progress</Link>}>
        <div className="grid gap-5 sm:grid-cols-3">
          {targets.map((t) => {
            const series = ms.filter((m) => m.metric === t.metric || (t.metric === "steps" && m.metric === "steps"));
            const latest = series.at(-1)?.value ?? t.baseline;
            const pct = Math.max(0, Math.min(1, (latest - t.baseline) / (t.target - t.baseline || 1)));
            const meta = METRIC_META[t.metric];
            return (
              <div key={t.metric}>
                <p className="text-sm text-ink-2">{t.label}</p>
                <p className="mt-1 text-2xl font-semibold">{latest.toLocaleString("en-CA")} <span className="text-sm font-normal text-muted">{meta?.unit}</span></p>
                <div className="mt-2 h-2 rounded-full bg-moss-soft" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct * 100)} aria-label={`${t.label} progress to target`}>
                  <div className="h-2 rounded-full bg-series" style={{ width: `${pct * 100}%` }} />
                </div>
                <p className="mt-1 text-xs text-muted">Baseline {t.baseline.toLocaleString("en-CA")} → target {t.target.toLocaleString("en-CA")}</p>
              </div>
            );
          })}
          {targets.length === 0 && <p className="text-sm text-muted">Targets are set in your Blueprint session.</p>}
        </div>
      </Panel>
    </>
  );
}
