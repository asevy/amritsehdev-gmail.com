import type { Metadata } from "next";
import Link from "next/link";
import { Container, SectionHeading, EntityTag, HypothesisBadge, Notice, ArrowLink } from "@/components/ui";
import { PLANS, ADD_ONS, CLINICAL_FEES, planPrice } from "@/config/catalog";
import { activeVariant } from "@/lib/commerce";
import { track } from "@/lib/analytics";
import { cad, cadExact } from "@/lib/money";
import { taxFor } from "@/config/tax";

export const metadata: Metadata = { title: "Programmes & pricing" };

export default async function ProgrammesPage() {
  const variant = activeVariant();
  await track("plan_viewed", { variant });
  const main = PLANS.filter((p) => p.id !== "maintenance");
  const maintenance = PLANS.find((p) => p.id === "maintenance")!;

  return (
    <>
      <section className="border-b border-line">
        <Container className="py-16">
          <p className="eyebrow">Programmes & pricing</p>
          <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05] sm:text-6xl">Clear prices. Clear limits. Cancel online.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
            Memberships are sold by RECLAIM and cover coaching, your plan and the library. Medical care and medication are separate — provided and billed by
            the independent medical practice and the pharmacy you choose — and are never bundled into a membership price.
          </p>
          <div className="mt-6 flex flex-wrap gap-2 text-sm">
            <span className="chip border-line-2 bg-card text-ink-2">Monthly · no minimum term</span>
            <span className="chip border-line-2 bg-card text-ink-2">Prices in CAD, plus HST</span>
            <span className="chip border-line-2 bg-card text-ink-2">Full refund within 14 days of first payment</span>
          </div>
        </Container>
      </section>

      <Container className="py-14">
        <div className="grid gap-5 lg:grid-cols-4">
          {main.map((p) => {
            const price = planPrice(p, variant);
            return (
              <div key={p.id} className={`card flex flex-col p-6 ${p.highlight ? "ring-2 ring-ink" : ""}`}>
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-2xl">{p.name}</h2>
                  {p.highlight && <span className="chip border-ink bg-ink text-paper">Most chosen</span>}
                </div>
                <p className="mt-4 font-mono text-4xl tabular-nums">{cad(price)}</p>
                <p className="text-xs text-muted">per month + HST ({cadExact(taxFor(p.taxCode, "ON", price).cents)}) · <HypothesisBadge /></p>
                <p className="mt-4 text-sm leading-6 text-ink-2">{p.audience}</p>
                <p className="eyebrow mt-6">Includes</p>
                <ul className="mt-2 space-y-2 text-sm">
                  {p.includes.map((i) => (
                    <li key={i} className="flex gap-2"><span className="text-moss" aria-hidden="true">✓</span>{i}</li>
                  ))}
                </ul>
                <p className="eyebrow mt-5">Limits</p>
                <ul className="mt-2 flex-1 space-y-2 text-sm text-ink-2">
                  {p.limits.map((i) => (
                    <li key={i} className="flex gap-2"><span className="text-muted" aria-hidden="true">–</span>{i}</li>
                  ))}
                </ul>
                <Link href={`/join?plan=${p.id}`} className={`mt-6 ${p.highlight ? "btn-primary" : "btn-ghost"}`}>Choose {p.name}</Link>
                <div className="mt-3"><EntityTag entity="platform" label="Sold by RECLAIM" /></div>
              </div>
            );
          })}
        </div>

        <div className="mt-5 card flex flex-wrap items-center justify-between gap-4 p-6">
          <div>
            <h2 className="text-2xl">{maintenance.name} <span className="ml-2 font-mono text-xl">{cad(planPrice(maintenance, variant))}/mo</span></h2>
            <p className="mt-1 text-sm text-ink-2">{maintenance.audience} {maintenance.eligibility}</p>
          </div>
          <p className="max-w-md text-sm text-ink-2">{maintenance.includes.join(" · ")}</p>
        </div>

        <p className="mt-6 text-sm text-muted">
          Pilot prices are under test and may change for new members; your price is shown before you pay and stays fixed for your current billing month.
          We never offer different prices to different visitors at the same time.
        </p>
      </Container>

      <Container className="grid gap-10 border-t border-line py-14 lg:grid-cols-2">
        <div>
          <SectionHeading eyebrow="Add-ons" title="Pay only for extra support you want." />
          <ul className="mt-6 divide-y divide-line rounded-2xl border border-line bg-card">
            {ADD_ONS.map((a) => (
              <li key={a.id} className="flex items-start justify-between gap-6 p-5">
                <div>
                  <p className="font-semibold">{a.name}</p>
                  <p className="mt-1 text-sm leading-6 text-ink-2">{a.description}</p>
                </div>
                <p className="shrink-0 font-mono">{cad(a.priceCents)}</p>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center gap-2"><EntityTag entity="platform" label="Sold by RECLAIM" /> <HypothesisBadge /></div>
        </div>
        <div>
          <SectionHeading eyebrow="Credits" title="How local-network credits work.">
            One credit is roughly one partner gym visit or small-group class. A 1:1 personal-training session is three credits; a body-composition scan is
            two. Cancel at least 24 hours ahead to get the credit back.
          </SectionHeading>
          <div className="mt-4"><ArrowLink href="/network">See partner types and areas</ArrowLink></div>
        </div>
      </Container>

      <section className="border-y border-line bg-bone/50">
        <Container className="grid gap-10 py-14 lg:grid-cols-2">
          <div>
            <EntityTag entity="clinical" />
            <h2 className="mt-4 text-3xl">Medical care is billed separately — and usually not to you.</h2>
            <p className="mt-3 text-[15px] leading-7 text-ink-2">
              The independent medical practice bills OHIP for insured services. You never need a RECLAIM membership to be seen, and a membership never
              buys faster access to insured care.
            </p>
            <table className="mt-6 w-full overflow-hidden rounded-2xl border border-line bg-card text-left text-sm">
              <caption className="sr-only">Medical practice fee schedule</caption>
              <thead className="bg-bone text-xs uppercase tracking-wider text-muted">
                <tr><th className="p-3">Service</th><th className="p-3">Insured?</th><th className="p-3">If uninsured</th></tr>
              </thead>
              <tbody className="divide-y divide-line">
                {CLINICAL_FEES.map((f) => (
                  <tr key={f.service}><td className="p-3">{f.service}</td><td className="p-3">{f.insured}</td><td className="p-3 text-muted">{f.uninsuredFee}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <EntityTag entity="pharmacy" />
            <h2 className="mt-4 text-3xl">Medication is priced by the pharmacy you choose.</h2>
            <p className="mt-3 text-[15px] leading-7 text-ink-2">
              If a clinician prescribes something, you choose where to fill it. The pharmacy sets the price, bills your drug plan, and shows you the cost
              before you pay. Your membership tier never changes what you pay for medication.
            </p>
            <div className="mt-6 space-y-3">
              <Notice title="No medication prices before a prescription">
                We don&apos;t list or promote prescription medicines on this website. If you&apos;re prescribed something, the pharmacy shows its price in your
                portal.
              </Notice>
              <ArrowLink href="/pharmacy">How pharmacy choice works</ArrowLink>
            </div>
          </div>
        </Container>
      </section>

      <Container className="py-14">
        <SectionHeading eyebrow="Cancelling" title="Two clicks, online, any time." />
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {[
            ["Cancel", "In Billing, any time. Your membership runs to the end of the month you've paid for. No fees, no phone call."],
            ["Pause instead", "Pause for a month on the same screen. Your plan, data and library stay put."],
            ["Refunds", "Full refund if you cancel within 14 days of your first payment. Refunds never depend on any medical decision."],
          ].map(([h, p]) => (
            <div key={h} className="card p-5"><p className="font-semibold">{h}</p><p className="mt-1 text-sm leading-6 text-ink-2">{p}</p></div>
          ))}
        </div>
        <div className="mt-4"><ArrowLink href="/legal/cancellation">Full cancellation and refund policy</ArrowLink></div>
      </Container>
    </>
  );
}
