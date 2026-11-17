import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Container, EntityTag, Notice, HypothesisBadge } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { buildCart, agreementSnapshot } from "@/lib/commerce";
import { confirmOrder } from "@/app/actions/commerce";
import { track } from "@/lib/analytics";
import { cadExact } from "@/lib/money";

export const metadata: Metadata = { title: "Review your order" };

export default async function ReviewPage({ searchParams }: { searchParams: Promise<{ plan?: string; addons?: string | string[]; code?: string; error?: string }> }) {
  const user = await requireUser(["member"]);
  const sp = await searchParams;
  const addOns = ([] as string[]).concat(sp.addons ?? []);
  let cart;
  try {
    cart = buildCart({ planId: sp.plan ?? "", addOnIds: addOns, province: user.province ?? "ON", sponsorCode: sp.code ?? null });
  } catch {
    redirect("/join");
  }
  const a = agreementSnapshot(cart, user);
  await track("order_review_viewed", { plan: cart.plan.id, variant: cart.variant }, user.id);
  const qs = new URLSearchParams({ plan: cart.plan.id, ...(sp.code ? { code: sp.code } : {}) });
  addOns.forEach((x) => qs.append("addons", x));

  return (
    <Container className="py-14">
      <p className="eyebrow">Step 4 of 5 · Review and agree</p>
      <h1 className="mt-3 text-4xl font-medium sm:text-5xl">Review your agreement</h1>
      <p className="mt-3 max-w-2xl text-ink-2">Please read this before you pay. A copy is emailed to you as soon as your payment goes through, and it&apos;s always available in Billing.</p>

      <div className="mt-10 grid gap-10 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="space-y-6">
          <section className="card p-6">
            <div className="flex items-center justify-between"><h2 className="font-sans text-lg font-semibold">Supplier</h2><EntityTag entity="platform" /></div>
            <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[140px_1fr]">
              <dt className="text-muted">Legal name</dt><dd>{a.supplier.legalName}</dd>
              <dt className="text-muted">Address</dt><dd>{a.supplier.address}</dd>
              <dt className="text-muted">Contact</dt><dd>{a.supplier.email} · {a.supplier.phone}</dd>
            </dl>
          </section>

          <section className="card p-6">
            <h2 className="font-sans text-lg font-semibold">What you&apos;re buying — {cart.plan.name}</h2>
            <ul className="mt-3 space-y-1.5 text-sm">
              {cart.plan.includes.map((i) => <li key={i} className="flex gap-2"><span className="text-moss">✓</span>{i}</li>)}
              {cart.plan.limits.map((i) => <li key={i} className="flex gap-2 text-ink-2"><span className="text-muted">–</span>{i}</li>)}
            </ul>
            <p className="mt-4 text-sm text-ink-2"><strong>Starts:</strong> {a.startDate} (today) · Your Blueprint session can be booked straight after payment.</p>
          </section>

          <section className="card p-6">
            <h2 className="font-sans text-lg font-semibold">Renewal, cancellation and refunds</h2>
            <dl className="mt-3 space-y-3 text-sm leading-6">
              <div><dt className="font-medium">Renewal</dt><dd className="text-ink-2">{a.renewal}</dd></div>
              <div><dt className="font-medium">Cancellation</dt><dd className="text-ink-2">{a.cancellation}</dd></div>
              <div><dt className="font-medium">Refunds</dt><dd className="text-ink-2">{a.refunds}</dd></div>
              <div><dt className="font-medium">Not included</dt><dd className="text-ink-2">{a.notIncluded}</dd></div>
            </dl>
          </section>
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <form action={confirmOrder} className="card p-6">
            <input type="hidden" name="plan" value={cart.plan.id} />
            {addOns.map((x) => <input key={x} type="hidden" name="addons" value={x} />)}
            {sp.code && <input type="hidden" name="code" value={sp.code} />}
            <input type="hidden" name="qs" value={qs.toString()} />
            <p className="eyebrow">Order · CAD</p>
            <table className="mt-3 w-full text-sm">
              <tbody>
                {cart.lines.map((l) => (
                  <tr key={l.sku}><td className="py-1 pr-3">{l.description}</td><td className="py-1 text-right font-mono">{cadExact(l.unitCents)}</td></tr>
                ))}
                <tr className="border-t border-line"><td className="pt-2 text-muted">Subtotal</td><td className="pt-2 text-right font-mono">{cadExact(cart.subtotalCents)}</td></tr>
                <tr><td className="text-muted">{cart.taxLabel}</td><td className="text-right font-mono">{cadExact(cart.taxCents)}</td></tr>
                <tr className="border-t border-line text-base font-semibold"><td className="pt-2">Total today</td><td className="pt-2 text-right font-mono">{cadExact(cart.totalCents)}</td></tr>
                <tr><td className="pt-1 text-xs text-muted">Then monthly</td><td className="pt-1 text-right font-mono text-xs text-muted">{cadExact(cart.renewalCents)}</td></tr>
              </tbody>
            </table>
            <div className="mt-2"><HypothesisBadge /></div>
            <label className="mt-5 flex items-start gap-3 text-sm leading-6">
              <input type="checkbox" name="agree" required className="mt-1 size-4 shrink-0 accent-ink" />
              <span>I have read this agreement, including automatic monthly renewal and how to cancel, and I agree to it.</span>
            </label>
            {sp.error === "agree" && <p role="alert" className="mt-2 text-sm text-ember">Please tick the box to agree.</p>}
            <button className="btn-primary mt-5 w-full">Agree and continue to payment</button>
            <Link href={`/join?plan=${cart.plan.id}`} className="btn-ghost mt-2 w-full">Edit order</Link>
            <div className="mt-4"><Notice>Card details are entered on the payment provider&apos;s secure page, not on RECLAIM&apos;s servers.</Notice></div>
          </form>
        </aside>
      </div>
    </Container>
  );
}
