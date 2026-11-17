/**
 * Site-wide configuration: legal entities, jurisdictions, contacts and feature flags.
 *
 * Every value in square brackets is a PLACEHOLDER that a founder or counsel must
 * replace before launch. The entity split below mirrors the business plan's
 * architecture: a commercial platform company, an independently owned and governed
 * medical practice, and a separately licensed pharmacy. The website attributes
 * every product, payment, record and message to exactly one of these.
 */

export type EntityId = "platform" | "clinical" | "pharmacy";

export interface LegalEntity {
  id: EntityId;
  /** Customer-facing short name. */
  displayName: string;
  /** Registered legal name (placeholder until incorporated). */
  legalName: string;
  role: string;
  /** Which Canadian privacy regime governs records this entity holds. */
  privacyRegime: string;
  address: string;
  email: string;
  phone: string;
  /** Statement descriptor that would appear on a card statement. */
  statementDescriptor: string;
}

export const ENTITIES: Record<EntityId, LegalEntity> = {
  platform: {
    id: "platform",
    displayName: "RECLAIM",
    legalName: "[RECLAIM Health Inc. — legal name TBD]",
    role:
      "Technology, coaching, programme design and the local partner network. Does not provide medical care or dispense medication.",
    privacyRegime: "PIPEDA (federal private-sector privacy law); acts as an agent / electronic service provider to the medical practice for clinical records under PHIPA",
    address: "[Registered office address, Ontario]",
    email: "support@[domain]",
    phone: "[1-8XX-XXX-XXXX]",
    statementDescriptor: "RECLAIM*MEMBERSHIP",
  },
  clinical: {
    id: "clinical",
    displayName: "[Independent Medical Practice]",
    legalName: "[Professional corporation / medical practice — legal name TBD]",
    role:
      "Independently owned and governed medical practice. Its physicians and nurse practitioners alone decide on assessment, investigations and any treatment, including whether to prescribe.",
    privacyRegime: "PHIPA (Ontario) — the practice is the health information custodian of your medical record",
    address: "[Practice address, Ontario]",
    email: "care@[practice-domain]",
    phone: "[Practice phone]",
    statementDescriptor: "[PRACTICE] MEDICAL",
  },
  pharmacy: {
    id: "pharmacy",
    displayName: "Your chosen pharmacy",
    legalName: "[Licensed partner pharmacy — legal name and OCP accreditation no. TBD]",
    role:
      "Dispenses prescriptions you choose to fill with it, adjudicates drug-plan claims and ships medication. You may fill any prescription at any pharmacy.",
    privacyRegime: "PHIPA (Ontario) — the pharmacy is a health information custodian for its dispensing record",
    address: "[Pharmacy address, Ontario]",
    email: "pharmacy@[pharmacy-domain]",
    phone: "[Pharmacy phone]",
    statementDescriptor: "[PHARMACY] RX",
  },
};

/** Jurisdictions. Only `live` jurisdictions can buy; others join the waitlist (which doubles as expansion-demand evidence). */
export type JurisdictionStatus = "live" | "waitlist" | "not_planned";
export interface Jurisdiction {
  code: string;
  name: string;
  country: "CA" | "US";
  status: JurisdictionStatus;
  clinicalAvailable: boolean;
  note?: string;
}

export const JURISDICTIONS: Jurisdiction[] = [
  { code: "ON", name: "Ontario", country: "CA", status: "live", clinicalAvailable: true },
  { code: "BC", name: "British Columbia", country: "CA", status: "waitlist", clinicalAvailable: false },
  { code: "AB", name: "Alberta", country: "CA", status: "waitlist", clinicalAvailable: false },
  { code: "MB", name: "Manitoba", country: "CA", status: "waitlist", clinicalAvailable: false },
  { code: "SK", name: "Saskatchewan", country: "CA", status: "waitlist", clinicalAvailable: false },
  { code: "NS", name: "Nova Scotia", country: "CA", status: "waitlist", clinicalAvailable: false },
  { code: "NB", name: "New Brunswick", country: "CA", status: "waitlist", clinicalAvailable: false },
  { code: "NL", name: "Newfoundland and Labrador", country: "CA", status: "waitlist", clinicalAvailable: false },
  { code: "PE", name: "Prince Edward Island", country: "CA", status: "waitlist", clinicalAvailable: false },
  {
    code: "QC", name: "Quebec", country: "CA", status: "waitlist", clinicalAvailable: false,
    note: "Requires French-first content and Quebec privacy (Law 25) review before launch.",
  },
  { code: "US", name: "United States (tell us your state)", country: "US", status: "waitlist", clinicalAvailable: false,
    note: "US launch requires separate entities, licensure and HIPAA programme. No Canadian registration carries over." },
];

export const LIVE_CODES = JURISDICTIONS.filter((j) => j.status === "live").map((j) => j.code);

export const SITE = {
  name: "RECLAIM",
  tagline: "Strength, body composition and metabolic health — measured.",
  /** Shown in footers and on every clinical surface. */
  emergency:
    "RECLAIM is not an emergency service. If you think you are having a medical emergency, call 911. In crisis or thinking about suicide, call or text 9-8-8.",
  supportHours: "Mon–Fri, 8am–6pm ET",
  /** Response-time promises must match coaching capacity in the financial model. */
  coachResponseSla: "1 business day",
  clinicalResponseSla: "2 business days for non-urgent clinical messages",
  /** Turns on demo-only affordances (demo logins, simulated pharmacy steps, test checkout). */
  demoMode: process.env.RECLAIM_DEMO_MODE !== "false",
  /** Analytics: first-party only, no third-party ad pixels on any page that collects health information. */
  thirdPartyPixels: false,
};
