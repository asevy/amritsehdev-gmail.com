import type { Metadata } from "next";
import { Container, SectionHeading, Notice, EntityTag } from "@/components/ui";
import { ENTITIES } from "@/config/site";

export const metadata: Metadata = { title: "About & governance" };

export default function AboutPage() {
  return (
    <>
      <Container className="py-16">
        <p className="eyebrow">About</p>
        <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05]">Built to measure, built to be trusted.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
          RECLAIM started from a simple observation: people changing their body composition need a plan for strength, food, sleep and habits — and
          sometimes medical care — and those pieces are usually sold separately, by people who never talk to each other.
        </p>
      </Container>

      <Container className="grid gap-5 md:grid-cols-2">
        <div className="card p-6">
          <p className="eyebrow">Founder</p>
          <p className="mt-2 text-2xl">[Founder name]</p>
          <p className="mt-1 text-sm text-ink-2">[Role and short biography — to be supplied by the founder]</p>
        </div>
        <div className="card p-6">
          <p className="eyebrow">Founder</p>
          <p className="mt-2 text-2xl">[Co-founder name]</p>
          <p className="mt-1 text-sm text-ink-2">[Role and short biography]</p>
          <p className="mt-3 rounded-lg bg-warn-soft/60 p-3 text-xs leading-5 text-ink-2">
            Counsel review required: Ontario rules restrict a physician&apos;s name from appearing in advertising for products or services other than their own
            medical services (O. Reg. 114/94 s.6). How a physician co-founder is described here — and on the relationships page — must be settled by counsel.
          </p>
        </div>
      </Container>

      <section id="structure" className="mt-20 border-y border-line bg-bone/50">
        <Container className="py-16">
          <SectionHeading eyebrow="Structure & governance" title="Three organisations, each accountable for its own part." />
          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {(["platform", "clinical", "pharmacy"] as const).map((id) => {
              const e = ENTITIES[id];
              return (
                <div key={id} className="card p-6">
                  <EntityTag entity={id} />
                  <p className="mt-4 font-semibold">{e.legalName}</p>
                  <p className="mt-2 text-sm leading-6 text-ink-2">{e.role}</p>
                  <p className="mt-3 text-xs leading-5 text-muted">Privacy: {e.privacyRegime}</p>
                </div>
              );
            })}
          </div>
          <div className="mt-8 grid gap-4 lg:grid-cols-2">
            <Notice title="How money flows">
              You pay RECLAIM for memberships and add-ons, the pharmacy for medication, and the medical practice only for any uninsured service. The practice and
              pharmacy pay RECLAIM fixed, fair-market-value fees for technology and administrative services under written agreements — never a share of
              prescriptions, fills or clinical revenue.
            </Notice>
            <Notice title="How decisions are protected">
              Clinical decisions belong to the practice&apos;s clinicians and medical director. RECLAIM staff and founders can&apos;t see clinical records, and
              aggregate reports to RECLAIM never break results down by clinician.
            </Notice>
          </div>
          <p className="mt-6 text-sm text-muted">
            Ownership, directors and any financial interest of RECLAIM&apos;s founders in the practice or pharmacy are disclosed on the{" "}
            <a className="underline" href="/legal/relationships">relationships page</a>. [Content pending counsel.]
          </p>
        </Container>
      </section>
    </>
  );
}
