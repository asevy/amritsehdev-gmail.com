import Link from "next/link";
import { Container, Notice } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getOrder } from "@/lib/commerce";
import { cadExact } from "@/lib/money";

export default async function WelcomePage({ searchParams }: { searchParams: Promise<{ order?: string }> }) {
  const user = await requireUser(["member"]);
  const { order: orderId } = await searchParams;
  const order = orderId ? getOrder(orderId, user.id) : null;
  return (
    <Container className="py-16">
      <div className="mx-auto max-w-2xl text-center">
        <p className="eyebrow">Step 5 of 5 · You&apos;re in</p>
        <h1 className="mt-4 text-5xl font-medium">Welcome to RECLAIM, {user.name.split(" ")[0]}.</h1>
        {order && <p className="mt-4 text-ink-2">Paid {cadExact(order.total_cents)}. Your receipt and a copy of your agreement (fingerprint <code className="font-mono text-xs">{order.agreement_sha.slice(0, 12)}</code>) have been emailed to {user.email}.</p>}
      </div>
      <div className="mx-auto mt-12 grid max-w-4xl gap-4 md:grid-cols-3">
        {[
          ["1", "Book your Blueprint session", "/portal/appointments", "Pick a 60-minute slot with your coach."],
          ["2", "Run your baseline test", "/portal/library/sit-to-stand", "The 30-second sit-to-stand takes two minutes."],
          ["3", "Medical assessment (optional)", "/portal/care", "Request one from the independent practice — separate and optional."],
        ].map(([n, h, href, p]) => (
          <Link key={n} href={href} className="card group p-6 hover:border-line-2">
            <span className="font-mono text-sm text-ember">0{n}</span>
            <p className="mt-3 font-semibold group-hover:underline">{h}</p>
            <p className="mt-1 text-sm text-ink-2">{p}</p>
          </Link>
        ))}
      </div>
      <div className="mx-auto mt-8 max-w-2xl"><Notice>You can cancel online in Billing at any time. Cancelling within 14 days of this payment gets a full refund.</Notice></div>
      <div className="mt-8 text-center"><Link href="/portal" className="btn-primary">Go to my portal</Link></div>
    </Container>
  );
}
