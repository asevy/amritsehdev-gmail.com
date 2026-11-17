import type { Metadata } from "next";
import { Container, EntityTag, Notice, SectionHeading } from "@/components/ui";
import { PHARMACY_OPTIONS } from "@/config/partners";

export const metadata: Metadata = { title: "Pharmacy & your choice" };

export default function PharmacyPage() {
  return (
    <>
      <section className="border-b border-line bg-rx-soft/40">
        <Container className="py-16">
          <EntityTag entity="pharmacy" />
          <h1 className="mt-5 max-w-3xl text-5xl font-medium leading-[1.05]">If something is prescribed, you choose where to fill it.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
            When a clinician issues a prescription, your portal shows three options in random order, with none pre-selected. We record exactly what you
            were shown, so the choice can be audited.
          </p>
        </Container>
      </section>
      <Container className="py-14">
        <div className="grid gap-4 md:grid-cols-3">
          {PHARMACY_OPTIONS.map((o) => (
            <div key={o.id} className="card p-6">
              <p className="font-semibold">{o.title}</p>
              <p className="mt-2 text-sm leading-6 text-ink-2">{o.detail}</p>
              {o.disclosure && <p className="mt-3 rounded-lg bg-warn-soft/60 p-3 text-xs leading-5 text-ink-2">{o.disclosure}</p>}
            </div>
          ))}
        </div>
        <div className="mt-12 grid gap-10 lg:grid-cols-2">
          <SectionHeading eyebrow="If you choose the partner pharmacy" title="What happens next.">
            <ol className="mt-4 list-decimal space-y-2 pl-5 text-[15px]">
              <li>The prescription is sent to the pharmacy you chose.</li>
              <li>A pharmacist reviews it and, for a first fill, talks with you about how to use it safely.</li>
              <li>The pharmacy bills your drug plan and shows the remaining cost in your portal before you pay.</li>
              <li>You pay the pharmacy directly — it&apos;s the seller, not RECLAIM — and it ships to you, refrigerated if needed.</li>
            </ol>
          </SectionHeading>
          <div className="space-y-4">
            <Notice title="Prices are the pharmacy's, not ours">
              The pharmacy&apos;s price for a medicine depends only on the product, quantity and your drug-plan coverage. It never depends on your RECLAIM
              membership, and RECLAIM offers no discounts, points or rewards linked to prescriptions.
            </Notice>
            <Notice tone="warn" title="Compounded and unapproved products">
              The medical practice prescribes only Health Canada-authorised products on its governance-approved formulary. We do not sell or promote
              &quot;research&quot; peptides or unapproved products.
            </Notice>
          </div>
        </div>
      </Container>
    </>
  );
}
