import type { EntityId } from "@/config/site";

/**
 * DRAFT legal and policy pages. These are structured outlines written to make the
 * site's commitments explicit and testable — they are NOT legal advice and must be
 * replaced or approved by qualified Ontario counsel before launch. `basis` lists the
 * authorities each page is designed around (verified 2026-11 — see docs/COMPLIANCE_REGISTER.md).
 */
export interface LegalDoc {
  slug: string;
  title: string;
  entity: EntityId;
  summary: string;
  sections: { h: string; p: string[] }[];
  basis: string[];
}

export const LEGAL_DOCS: LegalDoc[] = [
  {
    slug: "terms",
    title: "Terms of service & membership agreement",
    entity: "platform",
    summary: "The agreement between you and RECLAIM for memberships, add-ons and use of the site.",
    sections: [
      { h: "Who you're contracting with", p: ["[RECLAIM Health Inc.] provides coaching, programme design, digital tools and access to a local partner network. RECLAIM does not provide medical care, does not dispense medication and is not your health information custodian for medical records."] },
      { h: "What a membership includes — and doesn't", p: ["Each programme's inclusions and limits are listed on the Programmes page and in your order summary, which forms part of this agreement.", "Memberships never include, and never buy access to or priority for, insured medical services. Medical services are provided by an independent medical practice under its own terms; medication is sold by the pharmacy you choose."] },
      { h: "Price, renewal and changes", p: ["Memberships renew monthly at the price in your order summary until you cancel. We will give at least 30 days' notice of any price change and you may cancel before it takes effect."] },
      { h: "Cancellation and refunds", p: ["See the Cancellation & refunds policy. You may cancel online at any time."] },
      { h: "Coaching is not medical advice", p: ["Coaches provide exercise, nutrition-habit and behaviour coaching. They do not diagnose, treat or advise on medication. Seek medical advice for symptoms or medical questions."] },
      { h: "Assumption of risk & partner sessions", p: ["[Exercise-risk acknowledgement, partner-session terms and limitation of liability — counsel to draft; must be consistent with the Consumer Protection Act, 2002.]"] },
    ],
    basis: ["Consumer Protection Act, 2002 (Ontario) ss.29–40; O. Reg. 17/05 — personal development services and internet agreements", "Commitment to the Future of Medicare Act, 2004 ss.10, 17"],
  },
  {
    slug: "privacy",
    title: "Privacy notice — RECLAIM",
    entity: "platform",
    summary: "How RECLAIM collects, uses and protects personal information for coaching, programme and account services.",
    sections: [
      { h: "What we collect", p: ["Account details; your Blueprint (goals, capacity, pain limitations as you describe them, nutrition preferences, schedule, sleep, barriers and coaching preferences); measurements you log; plan and video activity; bookings; messages with your coach; payment records (card data is held by our payment processor, not us)."] },
      { h: "What we don't do", p: ["We do not sell personal information. We do not use third-party advertising pixels or trackers. We do not share your information with your employer."] },
      { h: "Separate consents", p: ["Marketing email, sharing coaching data with your clinical team, de-identified research use and product analytics are separate choices, off by default, that you can change at any time in Privacy settings. We keep a record of each choice and the exact wording you saw."] },
      { h: "Medical records", p: ["Your medical record is held by the independent medical practice as health information custodian under PHIPA. Where RECLAIM's systems store or display it, RECLAIM acts only as the practice's agent or electronic service provider, under a written agreement, and every access is logged."] },
      { h: "Where data is stored", p: ["[Canadian data residency commitment — confirm with hosting, email, payment and video vendors.]"] },
      { h: "Your rights", p: ["Download your RECLAIM data from Privacy settings at any time. You can ask us to correct or delete it; we keep financial records as required by tax law and proof of your consents."] },
      { h: "Contact", p: ["Privacy Officer: [name], privacy@[domain]. You may complain to the Office of the Privacy Commissioner of Canada."] },
    ],
    basis: ["PIPEDA s.4(1)(a), Schedule 1 principles", "CASL ss.6, 10, 11; SOR/2012-36", "PHIPA s.17; O. Reg. 329/04 s.6 (agent / electronic service provider)"],
  },
  {
    slug: "clinical-privacy",
    title: "Statement of information practices — medical practice",
    entity: "clinical",
    summary: "How the independent medical practice handles your personal health information as health information custodian.",
    sections: [
      { h: "Custodian", p: ["[Independent Medical Practice] is the health information custodian of your medical record under Ontario's Personal Health Information Protection Act, 2004 (PHIPA)."] },
      { h: "Service providers", p: ["The practice uses RECLAIM's platform as an electronic service provider / agent to host the patient portal, questionnaires, messaging and booking. RECLAIM may use your health information only to provide that service to the practice and may not disclose it. Founders and staff of RECLAIM who are not part of your care team cannot view your record."] },
      { h: "Sharing within your circle of care", p: ["With your consent, visit summaries are sent to your primary-care provider. A prescription is sent only to the pharmacy you choose. A short care summary goes to your RECLAIM coach only if you turn that on."] },
      { h: "Access, correction and complaints", p: ["You can request access to or correction of your record from the practice's privacy contact: [name, email]. You may complain to the Information and Privacy Commissioner of Ontario."] },
    ],
    basis: ["PHIPA ss.16, 17, 52–55", "O. Reg. 329/04 s.6", "CPSO Professional Obligations (2026)"],
  },
  {
    slug: "cancellation",
    title: "Cancellation & refunds",
    entity: "platform",
    summary: "How to cancel, pause, and when you get money back.",
    sections: [
      { h: "Cancel online, any time", p: ["Go to Portal → Billing → Cancel. It takes two clicks. Your membership continues until the end of the month you've paid for, then stops. No fees and no phone call."] },
      { h: "Cooling-off and refunds", p: ["Ontario law may give you a 10-day cooling-off period after you enter the agreement. RECLAIM gives you a full refund if you cancel within 14 days of your first payment, which covers that period.", "After 14 days, cancelling stops future charges; the current month isn't refunded. Unused add-ons (for example unused credits) are refundable on request."] },
      { h: "Refunds never depend on clinical decisions", p: ["Whether or not a clinician prescribes anything has no effect on any refund. That keeps clinical decisions free of commercial pressure."] },
      { h: "Pause", p: ["You can pause for one month instead of cancelling. Nothing is charged while paused."] },
      { h: "Cancelling doesn't affect medical care", p: ["Your care with the independent medical practice, and any prescription, continue regardless of your membership."] },
      { h: "Advance payments", p: ["We don't take payment for services that aren't yet available. [If founding-member pre-sales are offered, counsel must confirm trust-account and refund requirements first.]"] },
    ],
    basis: ["Consumer Protection Act, 2002 ss.29–31 (personal development services) and O. Reg. 17/05", "US (future): ROSCA; California Bus. & Prof. Code §17602 (AB 2863)"],
  },
  {
    slug: "relationships",
    title: "Relationships & disclosures",
    entity: "platform",
    summary: "Every financial relationship between RECLAIM, its founders, the medical practice, the pharmacy and partners.",
    sections: [
      { h: "Medical practice", p: ["[Ownership of the practice; any role of RECLAIM founders; the fixed, fair-market-value services fee the practice pays RECLAIM and what it covers. To be completed with counsel.]"] },
      { h: "Partner pharmacy", p: ["[Ownership of the pharmacy (must be pharmacist-majority under the Drug and Pharmacies Regulation Act); any interest of RECLAIM or its founders; fixed technology fee. To be completed with counsel.]", "You can fill prescriptions at any pharmacy. Options are shown in random order with none pre-selected."] },
      { h: "Local partners", p: ["Gyms, studios and trainers are paid a fixed wholesale rate per completed visit. Physiotherapists and dietitians pay RECLAIM nothing and receive nothing from RECLAIM for referrals."] },
      { h: "What no one is paid for", p: ["No one — clinician, coach, partner or RECLAIM — receives anything for a prescription being written, for which product is prescribed, or for which pharmacy fills it."] },
    ],
    basis: ["Drug and Pharmacies Regulation Act ss.142, 144; O. Reg. 264/16", "O. Reg. 130/17 (pharmacist conflicts)", "O. Reg. 114/94 ss.6–8, 16 (physician advertising, steering and conflicts)", "CPSO Professional Obligations (2026): Prescribing Drugs; Association with Products or Services"],
  },
  {
    slug: "accessibility",
    title: "Accessibility",
    entity: "platform",
    summary: "Our commitment to an accessible service and how to tell us about barriers.",
    sections: [
      { h: "Standard", p: ["We design to WCAG 2.1 Level AA, beyond the WCAG 2.0 AA required of large Ontario organisations. Every video has captions and a transcript; the site works with a keyboard and screen readers; we respect reduced-motion settings."] },
      { h: "Feedback", p: ["Tell us about any barrier at accessibility@[domain] or [phone]. We'll respond within [x] business days and can provide information in an accessible format on request."] },
    ],
    basis: ["AODA; O. Reg. 191/11 s.14 (Integrated Accessibility Standards)"],
  },
  {
    slug: "complaints",
    title: "Complaints",
    entity: "platform",
    summary: "Who to contact, depending on what went wrong.",
    sections: [
      { h: "About coaching, billing or the website", p: ["Email support@[domain]. We acknowledge within 2 business days and aim to resolve within 10."] },
      { h: "About medical care", p: ["Contact the medical practice at care@[practice-domain]. You may also contact the College of Physicians and Surgeons of Ontario or the College of Nurses of Ontario."] },
      { h: "About a pharmacy", p: ["Contact the pharmacy directly. You may also contact the Ontario College of Pharmacists."] },
      { h: "About privacy", p: ["RECLAIM: Office of the Privacy Commissioner of Canada. Medical or pharmacy records: Information and Privacy Commissioner of Ontario."] },
    ],
    basis: ["Regulated Health Professions Act, 1991 (college complaints)", "PIPEDA / PHIPA complaint routes"],
  },
];

export const legalBySlug = (slug: string) => LEGAL_DOCS.find((d) => d.slug === slug);
