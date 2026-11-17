/**
 * Local network. ALL ENTRIES ARE PLACEHOLDERS — no partner has been contacted or contracted.
 *
 * Two different arrangements, deliberately kept apart:
 *  - Wellness marketplace (gyms, studios, personal trainers): unregulated fitness services.
 *    Members spend RECLAIM credits; RECLAIM pays the partner a wholesale rate per
 *    completed visit under a written agreement.
 *  - Regulated providers (physiotherapists, dietitians): RECLAIM lists them as a directory
 *    only. The member books and pays the provider directly, and RECLAIM receives no
 *    referral fee or other benefit for the referral.
 */
export type PartnerType = "gym" | "studio" | "trainer" | "scan" | "physio" | "dietitian";

export interface Partner {
  id: string;
  name: string;
  type: PartnerType;
  regulated: boolean;
  area: string;
  booking: "credits" | "direct";
  credits?: number;
  sessionMinutes: number;
  description: string;
  /** Wholesale cost per completed visit (CAD cents) — ASSUMPTION pending partner quotes. */
  wholesaleCentsAssumption?: number;
}

export const PARTNERS: Partner[] = [
  {
    id: "p-gym-downtown",
    name: "[Partner gym] — Downtown Toronto",
    type: "gym",
    regulated: false,
    area: "Toronto (M5V)",
    booking: "credits",
    credits: 1,
    sessionMinutes: 60,
    description: "Open-gym visit with a programmed session from your coach loaded in the app.",
    wholesaleCentsAssumption: 1800,
  },
  {
    id: "p-studio-mississauga",
    name: "[Strength studio] — Mississauga",
    type: "studio",
    regulated: false,
    area: "Mississauga (L5B)",
    booking: "credits",
    credits: 1,
    sessionMinutes: 50,
    description: "Small-group strength class (max 8) for beginners and returners.",
    wholesaleCentsAssumption: 2200,
  },
  {
    id: "p-trainer-etobicoke",
    name: "[Personal trainer] — Etobicoke",
    type: "trainer",
    regulated: false,
    area: "Etobicoke (M8V)",
    booking: "credits",
    credits: 3,
    sessionMinutes: 55,
    description: "1:1 session with a certified trainer working from your Blueprint.",
    wholesaleCentsAssumption: 6500,
  },
  {
    id: "p-scan-northyork",
    name: "[Body-composition scan] — North York",
    type: "scan",
    regulated: false,
    area: "North York (M2N)",
    booking: "credits",
    credits: 2,
    sessionMinutes: 20,
    description: "Bioimpedance body-composition scan under standard conditions; results added to Progress.",
    wholesaleCentsAssumption: 3500,
  },
  {
    id: "p-physio-midtown",
    name: "[Physiotherapy clinic] — Midtown Toronto",
    type: "physio",
    regulated: true,
    area: "Toronto (M4S)",
    booking: "direct",
    sessionMinutes: 45,
    description: "Assessment and treatment for pain or injury before or during your programme. Often covered by extended health benefits.",
  },
  {
    id: "p-dietitian-virtual",
    name: "[Registered dietitian] — virtual, Ontario",
    type: "dietitian",
    regulated: true,
    area: "Virtual (Ontario)",
    booking: "direct",
    sessionMinutes: 45,
    description: "Medical nutrition therapy when you need more than coaching, e.g. alongside a medical condition.",
  },
];

export function partnerById(id: string): Partner | undefined {
  return PARTNERS.find((p) => p.id === id);
}

/** Booking rules for credit-based partner sessions (assumptions to validate with partners). */
export const CREDIT_RULES = {
  freeCancelHours: 24,
  lateCancelForfeits: true,
  rolloverMonths: 1,
};

/**
 * Pharmacy options presented when a prescription is issued. The aligned pharmacy is
 * one option among equals: options are shown in random order with identical styling,
 * no option is preselected, and the exact presentation is recorded.
 */
export const PHARMACY_OPTIONS = [
  {
    id: "aligned_pharmacy" as const,
    title: "[Partner pharmacy] — home delivery in Ontario",
    detail:
      "Ships to your door (refrigerated packaging when needed), bills most drug plans directly and offers pharmacist video consultations.",
    disclosure:
      "Disclosure: [describe the exact ownership or commercial relationship between RECLAIM, its founders and this pharmacy — to be finalised with counsel]. Your clinician is not paid more or less based on where you fill.",
  },
  {
    id: "other_pharmacy" as const,
    title: "Any other pharmacy you choose",
    detail: "Tell us the pharmacy's name and phone or fax number and your clinician will send the prescription there.",
    disclosure: null,
  },
  {
    id: "paper" as const,
    title: "A copy to take to a pharmacy yourself",
    detail: "Your clinician's office will provide a prescription you can take to any pharmacy.",
    disclosure: null,
  },
];
export type PharmacyChoice = (typeof PHARMACY_OPTIONS)[number]["id"];
