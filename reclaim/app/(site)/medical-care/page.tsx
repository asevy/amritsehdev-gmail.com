import type { Metadata } from "next";
import Link from "next/link";
import { Container, SectionHeading, EntityTag, Notice, EmergencyNotice, ArrowLink } from "@/components/ui";
import { ENTITIES } from "@/config/site";

export const metadata: Metadata = { title: "Medical care" };

/*
 * COMPLIANCE NOTE: this page describes a medical SERVICE. It must not name, picture or
 * promote any prescription drug, peptide or "treatment", and must not promise outcomes.
 * The compliance linter (npm run compliance) enforces the drug/claim list.
 */
export default function MedicalCarePage() {
  const clinic = ENTITIES.clinical;
  return (
    <>
      <section className="border-b border-line bg-clinic-soft/40">
        <Container className="grid gap-10 py-16 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <EntityTag entity="clinical" label={clinic.displayName} />
            <h1 className="mt-5 text-5xl font-medium leading-[1.05] sm:text-6xl">Medical care from an independent practice — when it&apos;s appropriate.</h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
              If you ask for it, a physician or nurse practitioner reviews your health history, orders any tests they think are needed, and talks with you
              about options. They decide, on their own clinical judgement, whether any treatment is appropriate. For many people the right plan is the
              programme alone.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/join?path=medical" className="btn-primary">Request a medical assessment</Link>
              <Link href="/assessment" className="btn-ghost">Start with the free assessment</Link>
            </div>
            <p className="mt-4 text-sm text-muted">No membership required. OHIP-insured services are never charged to you.</p>
          </div>
          <div className="card self-start p-6">
            <p className="eyebrow">Who provides it</p>
            <p className="mt-2 font-semibold">{clinic.legalName}</p>
            <p className="mt-2 text-sm leading-6 text-ink-2">{clinic.role}</p>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between gap-4"><dt className="text-muted">Privacy</dt><dd className="text-right">{clinic.privacyRegime}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted">Clinicians</dt><dd className="text-right">Names and CPSO/CNO registration numbers [to be listed]</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-muted">Medical director</dt><dd className="text-right">[Name, CPSO #]</dd></div>
            </dl>
          </div>
        </Container>
      </section>

      <Container className="grid gap-12 py-16 lg:grid-cols-2">
        <div>
          <SectionHeading eyebrow="What happens" title="Four steps, at your pace." />
          <ol className="mt-6 space-y-5">
            {[
              ["Health questionnaire", "Completed in your portal and sent only to the practice. RECLAIM coaches can't see it."],
              ["Video or phone visit", "With a physician or nurse practitioner licensed in Ontario, while you're in Ontario."],
              ["Tests if needed", "Requisitions for a community lab near you; results go to the practice and appear in your portal with the clinician's comments."],
              ["Shared decision", "You and the clinician agree a plan. If anything is prescribed, you choose the pharmacy, and follow-up and monitoring are scheduled."],
            ].map(([h, p], i) => (
              <li key={h} className="flex gap-4">
                <span className="mt-0.5 font-mono text-sm text-clinic">{String(i + 1).padStart(2, "0")}</span>
                <div><p className="font-semibold">{h}</p><p className="text-[15px] leading-7 text-ink-2">{p}</p></div>
              </li>
            ))}
          </ol>
        </div>
        <div className="space-y-4">
          <SectionHeading eyebrow="Independence" title="What the structure protects." />
          <ul className="mt-6 space-y-3 text-[15px] leading-7 text-ink-2">
            <li>• Clinicians are not paid more or less based on whether they prescribe, what they prescribe, or where you fill it.</li>
            <li>• Buying a membership never entitles you to a prescription, and refunds never depend on a clinical decision.</li>
            <li>• Your medical record belongs to the practice&apos;s custody, separate from RECLAIM&apos;s coaching records.</li>
            <li>• You can share coaching data with your clinician, or a short care summary with your coach — only if you choose to.</li>
          </ul>
          <ArrowLink href="/about#structure">Read about governance and relationships</ArrowLink>
        </div>
      </Container>

      <section className="border-y border-line bg-bone/50">
        <Container className="grid gap-10 py-14 lg:grid-cols-2">
          <div>
            <SectionHeading eyebrow="Is it for you?" title="When to see your own doctor instead." />
            <p className="mt-4 text-[15px] leading-7 text-ink-2">The practice may recommend in-person or specialist care instead of, or as well as, virtual care. Examples include:</p>
            <ul className="mt-3 space-y-2 text-[15px] leading-7 text-ink-2">
              <li>• You&apos;re under 18, pregnant, breastfeeding or planning pregnancy</li>
              <li>• You have, or have had, an eating disorder</li>
              <li>• Your health needs a physical examination or urgent investigation</li>
            </ul>
            <p className="mt-3 text-xs text-muted">Clinical eligibility criteria are set by the practice&apos;s medical director. [Draft list — clinical review required.]</p>
          </div>
          <div className="space-y-4">
            <EmergencyNotice />
            <Notice tone="clinical" title="Your family doctor stays in the loop">
              With your permission, the practice sends visit summaries to your primary-care provider. If you don&apos;t have one, the practice can tell you how
              to register with Health Care Connect.
            </Notice>
          </div>
        </Container>
      </section>
    </>
  );
}
