import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription, creditBalance } from "@/lib/commerce";
import { bookings, creditHistory } from "@/lib/portal-data";
import { bookPartnerSession, cancelBooking } from "@/app/actions/portal";
import { PARTNERS, CREDIT_RULES } from "@/config/partners";
import { PageHeader, Panel, MembershipRequired, Flash } from "@/components/portal";
import { fmtDate, fmtDateTime } from "@/lib/money";

function slots(): string[] {
  const out: string[] = [];
  for (let day = 2; day <= 6; day++) for (const h of [11, 22]) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() + day);
    d.setUTCHours(h, 0, 0, 0);
    out.push(d.toISOString());
  }
  return out;
}

const ERR: Record<string, string> = { credits: "Not enough credits for that session.", time: "Choose a time in the future.", partner: "That partner can't be booked with credits." };

export default async function NetworkPage({ searchParams }: { searchParams: Promise<{ booked?: string; error?: string }> }) {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const sp = await searchParams;
  const balance = creditBalance(user.id);
  const partnerBookings = bookings(user.id).filter((b) => b.kind === "partner");
  const upcoming = partnerBookings.filter((b) => b.status === "booked" && Date.parse(b.starts_at) > Date.now());
  return (
    <>
      <PageHeader eyebrow="Local network" title="Train in person" actions={<div className="card px-5 py-3 text-right"><p className="eyebrow">Credits</p><p className="text-3xl font-semibold">{balance}</p></div>}>
        Book partner gyms, studios, trainers and scans with credits. Cancel {CREDIT_RULES.freeCancelHours}+ hours ahead for your credit back.
      </PageHeader>
      {sp.booked && <Flash>Booked. Your coach has loaded the session plan for the partner.</Flash>}
      {sp.error && <Flash tone="err">{ERR[sp.error] ?? "Something went wrong."}</Flash>}
      {balance === 0 && <p className="mb-4 text-sm text-ink-2">Out of credits? <Link href="/portal/billing#addons" className="underline">Add 4 credits</Link>.</p>}

      <div className="grid gap-4 md:grid-cols-2">
        {PARTNERS.filter((p) => !p.regulated).map((p) => (
          <Panel key={p.id} title={p.name} action={<span className="font-mono text-sm">{p.credits} cr</span>}>
            <p className="text-sm text-muted">{p.area} · {p.sessionMinutes} min</p>
            <p className="mt-2 text-sm text-ink-2">{p.description}</p>
            <form action={bookPartnerSession} className="mt-4 flex gap-2">
              <input type="hidden" name="partnerId" value={p.id} />
              <select name="startsAt" className="input" aria-label={`Time for ${p.name}`}>{slots().map((s) => <option key={s} value={s}>{fmtDateTime(s)}</option>)}</select>
              <button className="btn-primary btn-sm shrink-0" disabled={balance < (p.credits ?? 99)}>Book</button>
            </form>
          </Panel>
        ))}
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Panel title="Upcoming partner sessions">
          {upcoming.length === 0 ? <p className="text-sm text-muted">None booked.</p> : (
            <ul className="divide-y divide-line">{upcoming.map((b) => (
              <li key={b.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <span>{b.title}<span className="block text-muted">{fmtDateTime(b.starts_at)}</span></span>
                <form action={cancelBooking}><input type="hidden" name="id" value={b.id} /><button className="btn-ghost btn-sm">Cancel</button></form>
              </li>
            ))}</ul>
          )}
        </Panel>
        <Panel title="Credit history">
          <ul className="space-y-1.5 text-sm">{creditHistory(user.id).map((c, i) => (
            <li key={i} className="flex justify-between gap-4"><span>{c.reason}</span><span className={`tabular-nums ${c.delta > 0 ? "text-series" : "text-ink-2"}`}>{c.delta > 0 ? "+" : ""}{c.delta}<span className="ml-2 text-xs text-muted">{fmtDate(c.created_at)}</span></span></li>
          ))}</ul>
        </Panel>
      </div>

      <Panel title="Physiotherapy & dietitians — book directly" className="mt-5">
        <p className="text-sm text-ink-2">Regulated health professionals aren&apos;t booked with credits. Contact them directly; RECLAIM receives no referral fee.</p>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">{PARTNERS.filter((p) => p.regulated).map((p) => <li key={p.id} className="rounded-xl border border-line p-3 text-sm"><p className="font-medium">{p.name}</p><p className="text-muted">{p.area}</p></li>)}</ul>
      </Panel>
    </>
  );
}
