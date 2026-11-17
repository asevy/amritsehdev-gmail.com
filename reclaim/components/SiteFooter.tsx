import Link from "next/link";
import { Container, Logo } from "./ui";
import { ENTITIES, SITE } from "@/config/site";

const COLS = [
  {
    title: "Programme",
    links: [
      ["/how-it-works", "How it works"],
      ["/programmes", "Programmes & pricing"],
      ["/coaching", "Coaching"],
      ["/medical-care", "Medical care"],
      ["/pharmacy", "Pharmacy & your choice"],
      ["/network", "Local network"],
    ],
  },
  {
    title: "Evidence",
    links: [
      ["/learn", "Learn"],
      ["/outcomes", "Outcomes & methods"],
      ["/research", "Research"],
      ["/about", "About & governance"],
    ],
  },
  {
    title: "Work with us",
    links: [
      ["/employers", "Employers"],
      ["/organisations", "Clinics & gyms (licensing)"],
      ["/network#partner", "Become a partner"],
      ["/waitlist", "Outside Ontario? Join the waitlist"],
    ],
  },
  {
    title: "Legal",
    links: [
      ["/legal/terms", "Terms & membership agreement"],
      ["/legal/privacy", "Privacy (RECLAIM)"],
      ["/legal/clinical-privacy", "Privacy (medical practice)"],
      ["/legal/cancellation", "Cancellation & refunds"],
      ["/legal/relationships", "Relationships & disclosures"],
      ["/legal/accessibility", "Accessibility"],
      ["/legal/complaints", "Complaints"],
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="mt-24 bg-ink text-paper">
      <Container className="py-14">
        <div className="grid gap-10 md:grid-cols-[1.2fr_repeat(4,1fr)]">
          <div>
            <Logo inverted />
            <p className="mt-4 max-w-xs text-sm leading-6 text-paper/70">{SITE.tagline}</p>
            <p className="mt-4 text-xs text-paper/50">Available in Ontario. Other provinces and US states: waitlist.</p>
          </div>
          {COLS.map((c) => (
            <div key={c.title}>
              <p className="eyebrow !text-paper/50">{c.title}</p>
              <ul className="mt-3 space-y-2">
                {c.links.map(([href, label]) => (
                  <li key={href}>
                    <Link href={href} className="text-sm text-paper/80 hover:text-paper">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 grid gap-4 border-t border-paper/15 pt-8 text-xs leading-5 text-paper/60 md:grid-cols-3">
          <p>
            <strong className="text-paper/85">RECLAIM</strong> is operated by {ENTITIES.platform.legalName}, a technology and coaching company. It does not
            practise medicine or dispense medication.
          </p>
          <p>
            <strong className="text-paper/85">Medical services</strong> are provided by {ENTITIES.clinical.displayName}, an independently owned and governed
            medical practice whose clinicians alone make clinical decisions. OHIP-insured services are never charged to patients.
          </p>
          <p>
            <strong className="text-paper/85">Prescriptions</strong> can be filled at any pharmacy you choose. Relationships between RECLAIM and any pharmacy
            are disclosed on our <Link href="/legal/relationships" className="underline">relationships page</Link>.
          </p>
        </div>
        <p className="mt-6 rounded-xl border border-paper/15 px-4 py-3 text-xs text-paper/70">{SITE.emergency}</p>
        <p className="mt-6 text-xs text-paper/40">
          Prototype build · all names in [brackets] are placeholders · legal pages are drafts pending counsel review.
        </p>
      </Container>
    </footer>
  );
}
