/**
 * Public RECLAIM assessment — lifestyle and preference questions only.
 *
 * Design rules (see docs/WEBSITE_SPEC.md §Assessment):
 *  - No diagnosis, no treatment, no medication suggestions. Output types are limited
 *    to a programme suggestion, focus areas and an optional "you can ask a clinician"
 *    pointer. A clinician — not this code — decides on anything medical. This keeps
 *    the questionnaire outside medical-device territory (to be confirmed by counsel).
 *  - Every suggestion carries a human-readable reason so the person can see why.
 *  - No weight, height or medical history is collected here. Answers stay in the
 *    browser (localStorage) until the person creates an account.
 */

export interface AssessmentAnswers {
  goals: string[];
  activity: "none" | "some" | "regular" | "";
  experience: "new" | "some" | "experienced" | "";
  sitToStand: "easily" | "with_effort" | "needs_hands" | "unsure" | "";
  pain: "none" | "some" | "significant" | "";
  daysPerWeek: number;
  minutesPerSession: number;
  setting: string[];
  cookingTime: "low" | "medium" | "high" | "";
  eatingPattern: string;
  sleepHours: number;
  stress: "low" | "medium" | "high" | "";
  barriers: string[];
  coachingStyle: "self" | "check_ins" | "live" | "in_person" | "";
  medicalInterest: "yes" | "maybe" | "no" | "";
  jurisdiction: string;
}

export const EMPTY_ANSWERS: AssessmentAnswers = {
  goals: [],
  activity: "",
  experience: "",
  sitToStand: "",
  pain: "",
  daysPerWeek: 3,
  minutesPerSession: 30,
  setting: [],
  cookingTime: "",
  eatingPattern: "",
  sleepHours: 7,
  stress: "",
  barriers: [],
  coachingStyle: "",
  medicalInterest: "",
  jurisdiction: "",
};

export const GOAL_OPTIONS = [
  { id: "strength", label: "Get stronger and move with confidence" },
  { id: "body_comp", label: "Change my body composition — less fat, keep or build muscle" },
  { id: "energy", label: "Have more energy through the day" },
  { id: "keep_off", label: "Keep results I've already worked for" },
  { id: "return", label: "Return to activity after time off or injury" },
  { id: "markers", label: "Improve health markers my own clinician has flagged" },
];

export const BARRIER_OPTIONS = [
  { id: "time", label: "Not enough time" },
  { id: "consistency", label: "Starting strong, then falling off" },
  { id: "knowledge", label: "Not sure what to do" },
  { id: "motivation", label: "Motivation" },
  { id: "cravings", label: "Hunger or cravings" },
  { id: "pain", label: "Pain or injury" },
  { id: "social", label: "Family, work or social pressures" },
  { id: "cost", label: "Cost" },
];

export const SETTING_OPTIONS = [
  { id: "home", label: "At home" },
  { id: "gym", label: "In a gym" },
  { id: "partner", label: "With a trainer or small group" },
  { id: "outdoors", label: "Outdoors" },
];

export type PathId = "foundation" | "core" | "hybrid" | "premium";

export interface AssessmentResult {
  plan: PathId;
  reasons: string[];
  focus: { title: string; detail: string }[];
  baselineTests: string[];
  physioFirst: boolean;
  medicalPointer: boolean;
  available: boolean;
}

export function suggestPath(a: AssessmentAnswers, liveCodes: string[]): AssessmentResult {
  const reasons: string[] = [];
  let plan: PathId = "core";

  switch (a.coachingStyle) {
    case "self":
      plan = "foundation";
      reasons.push("You prefer to work through a plan on your own.");
      if (a.experience === "new" && (a.barriers.includes("knowledge") || a.barriers.includes("consistency"))) {
        plan = "core";
        reasons.push("You're new to strength training and said consistency or knowing what to do gets in the way — two coached sessions a month usually help most at the start. Foundation is still an option.");
      }
      break;
    case "check_ins":
    case "live":
      plan = "core";
      reasons.push(a.coachingStyle === "live" ? "You want live time with a coach." : "You want regular check-ins with a coach who knows your plan.");
      break;
    case "in_person":
      plan = "hybrid";
      reasons.push("You train better in person, so your plan includes partner-gym or trainer sessions.");
      if (a.barriers.length >= 3 && a.stress === "high") {
        plan = "premium";
        reasons.push("You named several barriers and high stress — weekly coach contact gives more room to adjust.");
      }
      break;
    default:
      reasons.push("Core is where most people start.");
  }

  const physioFirst = a.pain === "significant";
  if (physioFirst) reasons.push("You reported significant pain. We suggest a physiotherapy assessment before loaded training — your coach adapts the plan meanwhile.");
  const medicalPointer = a.medicalInterest === "yes" || a.medicalInterest === "maybe";
  if (medicalPointer)
    reasons.push("You asked about medical care. You can request an assessment by the independent medical practice; its clinician decides whether any treatment is appropriate. It is never automatic and never part of the price of a membership.");

  const focus: AssessmentResult["focus"] = [];
  const days = Math.max(2, Math.min(4, a.daysPerWeek || 2));
  focus.push({
    title: `Strength foundation, ${days}× a week`,
    detail: `${a.minutesPerSession || 30}-minute sessions ${a.setting.includes("home") || a.setting.length === 0 ? "you can do at home" : "in the setting you chose"}, built around squat, hinge, push and pull patterns${a.pain !== "none" && a.pain ? ", adapted to your pain" : ""}.`,
  });
  if (a.goals.includes("body_comp") || a.goals.includes("keep_off"))
    focus.push({ title: "Protein at every meal", detail: "Spreading protein across the day supports muscle while body composition changes. Your coach sets a target with you." });
  if (a.sleepHours && a.sleepHours < 7)
    focus.push({ title: "A consistent sleep window", detail: `You reported about ${a.sleepHours} hours. Short sleep is linked with more hunger; we start with a fixed wake time.` });
  if (a.activity === "none" || a.activity === "some")
    focus.push({ title: "Daily walking baseline", detail: "We measure your current steps for a week, then build up gradually." });
  if (a.barriers.includes("consistency") || a.barriers.includes("time"))
    focus.push({ title: "Minimum-dose weeks", detail: "A fallback plan for busy weeks so a bad week doesn't end the programme." });

  const baselineTests = ["30-second sit-to-stand", "Waist circumference", "Weekly average steps", "Sleep log (7 days)"];
  if (a.sitToStand === "needs_hands") baselineTests[0] = "Supported sit-to-stand (with hands), progressing to unsupported";
  if (plan === "premium") baselineTests.push("In-person body-composition scan at a partner facility");

  return { plan, reasons, focus: focus.slice(0, 4), baselineTests, physioFirst, medicalPointer, available: liveCodes.includes(a.jurisdiction) };
}

/** Van Westendorp price-sensitivity summary over monthly coaching price responses (CAD). */
export function vanWestendorp(rows: Array<{ too_cheap: number; cheap: number; expensive: number; too_expensive: number }>) {
  if (rows.length === 0) return null;
  const prices = Array.from(new Set(rows.flatMap((r) => [r.too_cheap, r.cheap, r.expensive, r.too_expensive]))).sort((a, b) => a - b);
  const n = rows.length;
  const share = (pred: (r: (typeof rows)[number], p: number) => boolean, p: number) => rows.filter((r) => pred(r, p)).length / n;
  // Descending curves: share who think price p is too cheap / a bargain.
  // Ascending curves: share who think p is expensive / too expensive.
  const curve = prices.map((p) => {
    const cheap = share((r, x) => r.cheap >= x, p);
    const expensive = share((r, x) => r.expensive <= x, p);
    return {
      price: p,
      tooCheap: share((r, x) => r.too_cheap >= x, p),
      cheap,
      notCheap: 1 - cheap,
      expensive,
      notExpensive: 1 - expensive,
      tooExpensive: share((r, x) => r.too_expensive <= x, p),
    };
  });
  type K = keyof (typeof curve)[number];
  // First price at which the rising curve meets or passes the falling curve.
  const cross = (falling: K, rising: K) => curve.find((c) => (c[rising] as number) >= (c[falling] as number))?.price ?? null;
  return {
    n,
    curve,
    pointOfMarginalCheapness: cross("tooCheap", "notCheap"),
    optimalPricePoint: cross("tooCheap", "tooExpensive"),
    indifferencePricePoint: cross("cheap", "expensive"),
    pointOfMarginalExpensiveness: cross("notExpensive", "tooExpensive"),
  };
}
