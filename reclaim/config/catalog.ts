import type { EntityId } from "./site";
import type { TaxCode } from "./tax";

/**
 * Product catalogue.
 *
 * Products live in code (not an admin UI) on purpose: adding or changing anything
 * customers can buy goes through code review, the compliance linter
 * (scripts/compliance-lint.mjs) and, for anything clinical, the medical director.
 *
 * PRICES ARE HYPOTHESES. None of the prices below is derived from cost-to-serve,
 * supplier quotations or willingness-to-pay evidence yet. `priceStatus` stays
 * "hypothesis" until the financial model and a completed price test justify a
 * change; the admin Insights page reports the test results.
 *
 * The platform sells ONLY non-insured, non-pharmacy items. Medical services are
 * billed by the medical practice (OHIP-insured services are never charged to the
 * patient). Medication is sold by whichever pharmacy the patient chooses.
 */

export type PriceStatus = "hypothesis" | "tested" | "validated";

export interface Plan {
  id: "foundation" | "core" | "hybrid" | "premium" | "maintenance";
  name: string;
  merchant: Extract<EntityId, "platform">;
  taxCode: TaxCode;
  /** Monthly price in CAD cents, per price-test variant. Index 0 = control. */
  variantPriceCents: [number, number];
  priceStatus: PriceStatus;
  interval: "month";
  audience: string;
  includes: string[];
  /** Explicit limits — the plan must not promise unlimited personal access. */
  limits: string[];
  /** Workload drivers used for capacity planning (admin → Capacity). */
  workload: {
    liveMinutesPerMonth: number; // scheduled 1:1 coach time
    asyncMinutesPerMonth: number; // messaging, plan updates, check-in review
    blueprintMinutesOnce: number; // onboarding session, first month only
  };
  creditsPerMonth: number;
  /** Coach-reviewed form-check videos per month (each review ≈ FORM_CHECK_REVIEW_MINUTES of coach time). */
  formChecksPerMonth: number;
  eligibility?: string;
  highlight?: boolean;
}

export const PLANS: Plan[] = [
  {
    id: "foundation",
    name: "Foundation",
    merchant: "platform",
    taxCode: "taxable_service",
    variantPriceCents: [3900, 4900],
    priceStatus: "hypothesis",
    interval: "month",
    audience: "Self-directed people who want a structured, measured plan and a coach to ask.",
    includes: [
      "1 form-check video review a month: film a lift, get your coach's cues",
      "Personal plan generated from your assessment, reviewed by a coach",
      "Full video movement library and lesson curriculum",
      "Progress tracking and four-weekly re-test prompts",
      "Monthly live group Q&A with a coach",
    ],
    limits: [
      "Coach messaging: up to 4 conversations per month, replies within 2 business days",
      "No scheduled 1:1 sessions (add a Blueprint session any time)",
    ],
    workload: { liveMinutesPerMonth: 0, asyncMinutesPerMonth: 20, blueprintMinutesOnce: 0 },
    creditsPerMonth: 0,
    formChecksPerMonth: 1,
  },
  {
    id: "core",
    name: "Core",
    merchant: "platform",
    taxCode: "taxable_service",
    variantPriceCents: [14900, 17900],
    priceStatus: "hypothesis",
    interval: "month",
    audience: "Most people starting out: a coach who knows your plan and checks in on it.",
    includes: [
      "2 form-check video reviews a month: film a lift, get your coach's cues",
      "60-minute Blueprint session with your coach in month one",
      "Two 30-minute video sessions with your coach each month",
      "Plan updates every two weeks based on your logged data",
      "Everything in Foundation",
    ],
    limits: [
      "Coach messaging during support hours, replies within 1 business day",
      "Additional 1:1 sessions available as add-ons",
    ],
    workload: { liveMinutesPerMonth: 60, asyncMinutesPerMonth: 45, blueprintMinutesOnce: 60 },
    creditsPerMonth: 0,
    formChecksPerMonth: 2,
    highlight: true,
  },
  {
    id: "hybrid",
    name: "Hybrid",
    merchant: "platform",
    taxCode: "taxable_service",
    variantPriceCents: [24900, 28900],
    priceStatus: "hypothesis",
    interval: "month",
    audience: "People who train better in person and want sessions at a partner gym or with a trainer.",
    includes: [
      "4 form-check video reviews a month: film a lift, get your coach's cues",
      "Everything in Core",
      "4 local-network credits each month (about 4 partner gym visits or 1 personal-training session)",
      "Your coach programmes your partner sessions",
    ],
    limits: [
      "Unused credits roll over for one month, then expire",
      "Partner availability varies by neighbourhood — check the network map before joining",
    ],
    workload: { liveMinutesPerMonth: 60, asyncMinutesPerMonth: 60, blueprintMinutesOnce: 60 },
    creditsPerMonth: 4,
    formChecksPerMonth: 4,
  },
  {
    id: "premium",
    name: "Premium",
    merchant: "platform",
    taxCode: "taxable_service",
    variantPriceCents: [44900, 49900],
    priceStatus: "hypothesis",
    interval: "month",
    audience: "People who want weekly coaching contact and regular in-person measurement.",
    includes: [
      "8 form-check video reviews a month: film a lift, get your coach's cues",
      "Everything in Hybrid",
      "Weekly 30-minute video session with your coach",
      "8 local-network credits each month",
      "In-person body-composition scan at a partner facility every 12 weeks",
    ],
    limits: [
      "Coach messaging during support hours, replies the same business day when sent before 3pm",
      "Not 24/7 and not for urgent medical issues",
    ],
    workload: { liveMinutesPerMonth: 130, asyncMinutesPerMonth: 90, blueprintMinutesOnce: 60 },
    creditsPerMonth: 8,
    formChecksPerMonth: 8,
  },
  {
    id: "maintenance",
    name: "Maintenance",
    merchant: "platform",
    taxCode: "taxable_service",
    variantPriceCents: [6900, 8900],
    priceStatus: "hypothesis",
    interval: "month",
    audience: "Members who have reached their goals and want to keep them.",
    includes: [
      "1 form-check video review a month: film a lift, get your coach's cues",
      "Monthly 30-minute check-in with your coach",
      "Plan refresh every 4 weeks",
      "Full library and progress tracking",
    ],
    limits: ["Coach messaging: up to 4 conversations per month, replies within 2 business days"],
    workload: { liveMinutesPerMonth: 30, asyncMinutesPerMonth: 20, blueprintMinutesOnce: 0 },
    creditsPerMonth: 0,
    formChecksPerMonth: 1,
    eligibility: "Available after 6 months on Core, Hybrid or Premium.",
  },
];

export interface AddOn {
  id: string;
  name: string;
  description: string;
  merchant: Extract<EntityId, "platform">;
  taxCode: TaxCode;
  priceCents: number;
  priceStatus: PriceStatus;
  credits?: number;
  oneTime: true;
}

export const ADD_ONS: AddOn[] = [
  {
    id: "blueprint-session",
    name: "Blueprint session",
    description: "60-minute 1:1 session with a coach to build or rebuild your Blueprint. Included in Core and above.",
    merchant: "platform",
    taxCode: "taxable_service",
    priceCents: 12900,
    priceStatus: "hypothesis",
    oneTime: true,
  },
  {
    id: "credits-4",
    name: "4 local-network credits",
    description: "Use at partner gyms, studios and trainers. Credits expire 90 days after purchase.",
    merchant: "platform",
    taxCode: "taxable_service",
    priceCents: 11900,
    priceStatus: "hypothesis",
    credits: 4,
    oneTime: true,
  },
  {
    id: "coach-session",
    name: "Extra 30-minute coach session",
    description: "One additional video session with your coach.",
    merchant: "platform",
    taxCode: "taxable_service",
    priceCents: 5900,
    priceStatus: "hypothesis",
    oneTime: true,
  },
];

/**
 * Medical-practice fee schedule (shown for transparency; charged by the practice,
 * never by the platform). Insured status must be confirmed by the practice's OHIP
 * billing review and counsel. A patient never needs a RECLAIM membership to see
 * the practice, and buying a membership never buys faster access to insured care.
 */
export const CLINICAL_FEES = [
  {
    service: "Medical assessment (virtual)",
    insured: "OHIP-insured where eligible — no charge to you",
    uninsuredFee: "[Practice to set, if any service is uninsured]",
  },
  {
    service: "Follow-up and monitoring visits",
    insured: "OHIP-insured where eligible — no charge to you",
    uninsuredFee: "[Practice to set]",
  },
  {
    service: "Uninsured services (forms, letters, non-medically-necessary services)",
    insured: "Not insured",
    uninsuredFee: "[Per the practice's published fee schedule]",
  },
];

export function planById(id: string | null | undefined): Plan | undefined {
  return PLANS.find((p) => p.id === id);
}
export function addOnById(id: string): AddOn | undefined {
  return ADD_ONS.find((a) => a.id === id);
}
export function planPrice(plan: Plan, variant: number): number {
  return plan.variantPriceCents[variant === 1 ? 1 : 0];
}
