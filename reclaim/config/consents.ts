import type { EntityId } from "./site";

/**
 * Consent catalogue. Each consent is separate, unbundled and (unless required to
 * provide the service) off by default. The exact `text` is hashed and stored with
 * every grant or withdrawal, so we can prove what a person agreed to.
 *
 * DRAFT WORDING — must be finalised by privacy counsel (PIPEDA, PHIPA, CASL).
 */
export type ConsentKind =
  | "platform_terms"
  | "platform_privacy"
  | "marketing_email"
  | "coaching_to_clinical"
  | "clinical_summary_to_coach"
  | "research_deidentified"
  | "employer_aggregate"
  | "product_analytics";

export interface ConsentDef {
  kind: ConsentKind;
  entity: EntityId;
  label: string;
  text: string;
  required: boolean;
  version: string;
  /** Shown in the privacy centre; required consents are withdrawn by closing the account. */
  withdrawable: boolean;
}

export const CONSENTS: Record<ConsentKind, ConsentDef> = {
  platform_terms: {
    kind: "platform_terms",
    entity: "platform",
    label: "Terms of service",
    text: "I agree to the RECLAIM Terms of Service and Membership Agreement, including automatic monthly renewal until I cancel online.",
    required: true,
    version: "2026-11-draft",
    withdrawable: false,
  },
  platform_privacy: {
    kind: "platform_privacy",
    entity: "platform",
    label: "Privacy notice",
    text: "I have read the RECLAIM Privacy Notice and consent to RECLAIM collecting and using my information to provide coaching, programme and account services as described.",
    required: true,
    version: "2026-11-draft",
    withdrawable: false,
  },
  marketing_email: {
    kind: "marketing_email",
    entity: "platform",
    label: "Marketing email",
    text: "Send me RECLAIM news, offers and programme updates by email. I can unsubscribe at any time from any email or my privacy settings.",
    required: false,
    version: "2026-11-draft",
    withdrawable: true,
  },
  coaching_to_clinical: {
    kind: "coaching_to_clinical",
    entity: "platform",
    label: "Share my coaching data with my clinical team",
    text: "Share my Blueprint, logged measurements and plan adherence with clinicians of the independent medical practice treating me, so they can consider it in my care.",
    required: false,
    version: "2026-11-draft",
    withdrawable: true,
  },
  clinical_summary_to_coach: {
    kind: "clinical_summary_to_coach",
    entity: "clinical",
    label: "Let my clinician share a care summary with my coach",
    text: "Allow my clinician to share a short care-team summary (for example, exercise precautions) with my RECLAIM coach. It never includes diagnoses, test results or medication details unless I separately agree.",
    required: false,
    version: "2026-11-draft",
    withdrawable: true,
  },
  research_deidentified: {
    kind: "research_deidentified",
    entity: "platform",
    label: "De-identified research",
    text: "Allow my de-identified programme data to be used in research approved by a research ethics board. RECLAIM never sells personal information. Saying no does not affect my care.",
    required: false,
    version: "2026-11-draft",
    withdrawable: true,
  },
  employer_aggregate: {
    kind: "employer_aggregate",
    entity: "platform",
    label: "Employer-sponsored membership reporting",
    text: "I understand my employer pays for my membership and receives only aggregate statistics about groups of at least 10 people. My employer never receives my individual information.",
    required: false,
    version: "2026-11-draft",
    withdrawable: true,
  },
  product_analytics: {
    kind: "product_analytics",
    entity: "platform",
    label: "Product analytics",
    text: "Allow RECLAIM to use first-party analytics about how I use the site (pages and features, never health details) to improve the service. No third-party advertising trackers are used.",
    required: false,
    version: "2026-11-draft",
    withdrawable: true,
  },
};

/** Clinical-practice acknowledgements, recorded in the clinical store at enrolment. */
export const CLINICAL_ACKS = {
  privacy_notice:
    "I have read the medical practice's statement of information practices. The practice is the health information custodian of my medical record.",
  virtual_care:
    "I understand the benefits and limits of virtual care, that a clinician may ask me to attend in person, and that virtual care is not for emergencies.",
  independence:
    "I understand that the practice's clinicians alone decide whether any treatment, test or prescription is appropriate, and that buying a RECLAIM membership does not entitle me to any prescription.",
};
