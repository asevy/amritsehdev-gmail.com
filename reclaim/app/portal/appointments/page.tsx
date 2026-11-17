import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { bookings } from "@/lib/portal-data";
import { getEnrolment, listEncounters } from "@/lib/clinical";
import { bookCoachSession, cancelBooking } from "@/app/actions/portal";
import { PageHeader, Panel, MembershipRequired, Flash } from "@/components/portal";
import { EntityTag } from "@/components/ui";
import { fmtDateTime } from "@/lib/money";

function nextSlots(n: number): string[] {
  const out: string[] = [];
  const d = new Date();
  d.setUTCMinutes(0, 0, 0);
  while (out.length < n) {
    d.setUTCHours(d.getUTCHours() + 1);
    const torontoHour = (d.getUTCHours() + 19) % 24; // ~ET (UTC-5)
    const dow = d.getUTCDay();
    if (dow !== 0 && [8, 12, 17, 18].includes(torontoHour) && d.getTime() > Date.now() + 20 * 3600_000) out.push(d.toISOString());
  }
  return out;
}

export default async function AppointmentsPage({ searchParams }: { searchParams: Promise<{ booked?: string; error?: string }> }) {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const sp = await searchParams;
  const all = bookings(user.id);
  const upcoming = all.filter((b) => b.status === "booked" && Date.parse(b.starts_at) > Date.now());
  const past = all.filter((b) => !upcoming.includes(b)).reverse();
  const clinical = getEnrolment(user) ? listEncounters(user).filter((e) => e.status === "booked") : [];
  const hasBlueprint = all.some((b) => b.title.startsWith("Blueprint") && b.status !== "cancelled");
  return (
    <>
      <PageHeader eyebrow="Appointments" title="Your sessions" />
      {sp.booked && <Flash>Booked. A confirmation has been sent to {user.email}.</Flash>}
      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <div className="space-y-5">
          <Panel title="Upcoming">
            {upcoming.length + clinical.length === 0 && <p className="text-sm text-muted">Nothing booked.</p>}
            <ul className="divide-y divide-line">
              {upcoming.map((b) => (
                <li key={b.id} className="flex items-center justify-between gap-3 py-3">
                  <div><p className="font-medium">{b.title}</p><p className="text-sm text-muted">{fmtDateTime(b.starts_at)} · {b.duration_min} min{b.credits_used ? ` · ${b.credits_used} credit${b.credits_used > 1 ? "s" : ""}` : ""}</p></div>
                  <div className="flex items-center gap-2">
                    <EntityTag entity="platform" />
                    <form action={cancelBooking}><input type="hidden" name="id" value={b.id} /><button className="btn-ghost btn-sm">Cancel</button></form>
                  </div>
                </li>
              ))}
              {clinical.map((e) => (
                <li key={e.id} className="flex items-center justify-between gap-3 py-3">
                  <div><p className="font-medium">{e.kind === "initial" ? "Medical assessment" : "Medical follow-up"} — {e.clinician_name}</p><p className="text-sm text-muted">{fmtDateTime(e.starts_at)} · {e.modality}</p></div>
                  <Link href="/portal/care" className="flex items-center gap-2 text-sm underline"><EntityTag entity="clinical" /> Manage</Link>
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="Past">
            <ul className="space-y-2 text-sm">{past.slice(0, 8).map((b) => <li key={b.id} className="flex justify-between gap-4"><span>{b.title}</span><span className="text-muted">{fmtDateTime(b.starts_at)} · {b.status}</span></li>)}</ul>
          </Panel>
        </div>
        <Panel title="Book a coach session">
          <form action={bookCoachSession} className="space-y-4">
            <fieldset>
              <legend className="field-label">Type</legend>
              <label className="flex items-center gap-2 text-sm"><input type="radio" name="type" value="coach" defaultChecked={hasBlueprint} className="accent-ink" /> 30-minute coach session</label>
              <label className="mt-1 flex items-center gap-2 text-sm"><input type="radio" name="type" value="blueprint" defaultChecked={!hasBlueprint} className="accent-ink" /> 60-minute Blueprint session</label>
            </fieldset>
            <label className="block text-sm"><span className="field-label">Time (Eastern)</span>
              <select name="startsAt" className="input">{nextSlots(8).map((s) => <option key={s} value={s}>{fmtDateTime(s)}</option>)}</select>
            </label>
            <button className="btn-primary w-full">Book</button>
            <p className="text-xs text-muted">Reschedule or cancel up to 12 hours ahead. Live slots come from the scheduling system in production; these are generated for the demo.</p>
          </form>
        </Panel>
      </div>
    </>
  );
}
