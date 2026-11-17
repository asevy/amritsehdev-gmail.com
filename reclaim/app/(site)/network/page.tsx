import type { Metadata } from "next";
import { Container, SectionHeading, Notice } from "@/components/ui";
import { LeadForm } from "@/components/forms";
import { PARTNERS, CREDIT_RULES } from "@/config/partners";

export const metadata: Metadata = { title: "Local network" };

const TYPE_LABEL: Record<string, string> = { gym: "Gym", studio: "Studio", trainer: "Personal trainer", scan: "Body-composition scan", physio: "Physiotherapy", dietitian: "Registered dietitian" };

export default function NetworkPage() {
  const marketplace = PARTNERS.filter((p) => !p.regulated);
  const regulated = PARTNERS.filter((p) => p.regulated);
  return (
    <>
      <Container className="py-16">
        <p className="eyebrow">Local network · Greater Toronto Area first</p>
        <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05] sm:text-6xl">Train in person, near you, from the same plan.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
          Partner gyms, studios and trainers run the sessions your coach programmes. Results flow back into your portal. Partner names below are
          placeholders until agreements are signed.
        </p>
      </Container>
      <Container>
        <h2 className="text-3xl">Book with credits</h2>
        <p className="mt-2 text-ink-2">Included in Hybrid and Premium; available as an add-on for any plan.</p>
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {marketplace.map((p) => (
            <div key={p.id} className="card p-5">
              <p className="eyebrow">{TYPE_LABEL[p.type]}</p>
              <p className="mt-2 font-semibold">{p.name}</p>
              <p className="mt-1 text-sm text-muted">{p.area}</p>
              <p className="mt-3 text-sm leading-6 text-ink-2">{p.description}</p>
              <p className="mt-4 font-mono text-sm">{p.credits} credit{p.credits === 1 ? "" : "s"} · {p.sessionMinutes} min</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted">
          Cancel at least {CREDIT_RULES.freeCancelHours} hours ahead to get your credit back. Unused plan credits roll over for {CREDIT_RULES.rolloverMonths} month.
        </p>

        <h2 className="mt-16 text-3xl">Regulated health professionals</h2>
        <p className="mt-2 max-w-2xl text-ink-2">
          Physiotherapists and dietitians are listed as a directory. You book and pay them directly (often covered by extended health benefits). RECLAIM
          receives no referral fee or other benefit, and credits can&apos;t be used for regulated health services.
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {regulated.map((p) => (
            <div key={p.id} className="card p-5">
              <p className="eyebrow">{TYPE_LABEL[p.type]} · book directly</p>
              <p className="mt-2 font-semibold">{p.name}</p>
              <p className="mt-1 text-sm text-muted">{p.area}</p>
              <p className="mt-3 text-sm leading-6 text-ink-2">{p.description}</p>
            </div>
          ))}
        </div>
      </Container>

      <section id="partner" className="mt-20 border-y border-line bg-bone/50">
        <Container className="grid gap-10 py-16 lg:grid-cols-2">
          <div>
            <SectionHeading eyebrow="For gyms, studios & trainers" title="Become a RECLAIM partner.">
              Fill off-peak capacity with members who arrive with a plan. You&apos;re paid a fixed wholesale rate per completed visit under a written
              agreement. No exclusivity.
            </SectionHeading>
            <div className="mt-6">
              <Notice tone="warn" title="Partner standards">
                Partners must hold appropriate insurance and credentials, follow the member&apos;s programmed session, report attendance, and must not sell or
                promote prescription drugs, peptides or other unauthorised health products to members.
              </Notice>
            </div>
          </div>
          <div className="card p-6"><LeadForm kind="partner" sizeLabel="Number of staff" messageLabel="Location, capacity and off-peak hours" /></div>
        </Container>
      </section>
    </>
  );
}
