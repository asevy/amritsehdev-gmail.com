import { db, newId, audit, sha256 } from "./index";
import { hashPassword } from "../password";
import { CONSENTS, CLINICAL_ACKS, type ConsentKind } from "../../config/consents";

/**
 * Demo data so a fresh clone is explorable. EVERYTHING here is fictional:
 *  - demo people use the reserved .test domain;
 *  - formulary items and prices are placeholders, not real products or prices;
 *  - funnel events, waitlist rows, leads and price-survey answers are tagged
 *    "synthetic" and excluded from Admin → Insights unless explicitly included.
 */
export const DEMO_PASSWORD = "reclaim-demo";
export const DEMO_ACCOUNTS = [
  { email: "member@reclaim.test", role: "member", name: "Jordan Lee" },
  { email: "coach@reclaim.test", role: "coach", name: "Riley Morgan" },
  { email: "clinician@reclaim.test", role: "clinician", name: "Dr. Avery Demo" },
  { email: "pharmacist@reclaim.test", role: "pharmacist", name: "Sam Okafor, RPh" },
  { email: "founder@reclaim.test", role: "admin", name: "Founder (admin)" },
] as const;

const day = 86400_000;
const iso = (msAgo: number) => new Date(Date.now() - msAgo).toISOString();
const ago = (days: number, hour = 9) => {
  const d = new Date(Date.now() - days * day);
  d.setUTCHours(hour + 5, 0, 0, 0); // ~ET
  return d.toISOString();
};
const ahead = (days: number, hour = 9) => ago(-days, hour);

function mondayOfThisWeek(): string {
  const d = new Date();
  const dow = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dow);
  return d.toISOString().slice(0, 10);
}

// Deterministic PRNG for synthetic data
function rng(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };
}

export function seedDemoData(): void {
  const P = db("platform");
  const C = db("clinical");
  const R = db("pharmacy");
  const pw = hashPassword(DEMO_PASSWORD);

  const ids: Record<string, string> = {};
  for (const a of DEMO_ACCOUNTS) {
    const id = newId("usr");
    ids[a.role] = id;
    P.prepare("INSERT INTO users (id, email, pw_hash, name, role, province, patient_ref, created_at) VALUES (?,?,?,?,?,?,?,?)").run(
      id, a.email, pw, a.name, a.role, "ON", a.role === "member" ? crypto.randomUUID() : null, ago(70),
    );
  }
  const member = ids.member;
  const patientRef = (P.prepare("SELECT patient_ref FROM users WHERE id = ?").get(member) as { patient_ref: string }).patient_ref;

  // Consents
  const grant = (kind: ConsentKind, granted: boolean, at: string) =>
    P.prepare("INSERT INTO consents (user_id, kind, granted, version, text_sha, route, created_at) VALUES (?,?,?,?,?,?,?)").run(
      member, kind, granted ? 1 : 0, CONSENTS[kind].version, sha256(CONSENTS[kind].text), "/join", at,
    );
  grant("platform_terms", true, ago(70));
  grant("platform_privacy", true, ago(70));
  grant("marketing_email", false, ago(70));
  grant("product_analytics", true, ago(70));
  grant("coaching_to_clinical", true, ago(56));
  grant("clinical_summary_to_coach", true, ago(56));

  // Orders + subscription (Core, control price)
  const orderId = newId("ord");
  const agreement = JSON.stringify({ demo: true, note: "Seeded order — agreement snapshot omitted" });
  P.prepare(
    `INSERT INTO orders (id, user_id, status, province, subtotal_cents, tax_cents, total_cents, price_variant, agreement_json, agreement_sha, provider, provider_ref, created_at, paid_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
  ).run(orderId, member, "paid", "ON", 14900, 1937, 16837, 0, agreement, sha256(agreement), "mock", "mock_demo_1", ago(70), ago(70));
  P.prepare("INSERT INTO order_lines (order_id, sku, kind, description, qty, unit_cents, tax_code, tax_cents) VALUES (?,?,?,?,?,?,?,?)").run(
    orderId, "plan:core", "plan", "Core membership — first month", 1, 14900, "taxable_service", 1937,
  );
  const periodEnd = new Date();
  periodEnd.setUTCDate(periodEnd.getUTCDate() + 12);
  P.prepare(
    `INSERT INTO subscriptions (id, user_id, plan_id, status, price_cents, price_variant, order_id, started_at, current_period_end) VALUES (?,?,?,?,?,?,?,?,?)`,
  ).run(newId("sub"), member, "core", "active", 14900, 0, orderId, ago(70), periodEnd.toISOString());

  const creditOrder = newId("ord");
  P.prepare(
    `INSERT INTO orders (id, user_id, status, province, subtotal_cents, tax_cents, total_cents, price_variant, agreement_json, agreement_sha, provider, provider_ref, created_at, paid_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
  ).run(creditOrder, member, "paid", "ON", 11900, 1547, 13447, 0, agreement, sha256(agreement), "mock", "mock_demo_2", ago(21), ago(21));
  P.prepare("INSERT INTO order_lines (order_id, sku, kind, description, qty, unit_cents, tax_code, tax_cents) VALUES (?,?,?,?,?,?,?,?)").run(
    creditOrder, "addon:credits-4", "addon", "4 local-network credits", 1, 11900, "taxable_service", 1547,
  );
  P.prepare("INSERT INTO credits_ledger (user_id, delta, reason, ref, expires_at, created_at) VALUES (?,?,?,?,?,?)").run(member, 4, "4 local-network credits", creditOrder, ahead(69), ago(21));
  P.prepare("INSERT INTO credits_ledger (user_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)").run(member, -1, "Booked: [Strength studio] — Mississauga", "bk_demo_1", ago(14));
  P.prepare("INSERT INTO credits_ledger (user_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)").run(member, -1, "Booked: [Partner gym] — Downtown Toronto", "bk_demo_2", ago(1));

  // Bookings
  const bk = P.prepare("INSERT INTO bookings (id, user_id, kind, partner_id, title, starts_at, duration_min, status, credits_used) VALUES (?,?,?,?,?,?,?,?,?)");
  bk.run("bk_demo_1", member, "partner", "p-studio-mississauga", "Small-group strength class", ago(12, 18), 50, "completed", 1);
  bk.run("bk_demo_2", member, "partner", "p-gym-downtown", "Open gym — programmed session", ahead(2, 7), 60, "booked", 1);
  bk.run(newId("bk"), member, "coach", null, "Blueprint session with Riley", ago(68, 12), 60, "completed", 0);
  bk.run(newId("bk"), member, "coach", null, "Coach session (30 min)", ago(17, 12), 30, "completed", 0);
  bk.run(newId("bk"), member, "coach", null, "Coach session (30 min)", ahead(3, 12), 30, "booked", 0);

  // Blueprint versions (coaching side only)
  const bp1 = {
    goals: ["strength", "body_comp", "keep_off"],
    capacity: { sitToStand30s: 11, walk: "20 min comfortable", experience: "new" },
    painLimitations: "Intermittent right-knee discomfort on stairs; no high-impact jumping for now.",
    nutrition: { pattern: "Omnivore", cookingTime: "medium", notes: "Skips breakfast; large evening meal." },
    preferences: { setting: ["home", "partner"], enjoys: "Walking, small-group classes" },
    schedule: { daysPerWeek: 3, minutesPerSession: 30, bestTimes: "Early morning, weekends" },
    sleep: { hours: 6.1, notes: "Irregular wake time" },
    barriers: ["consistency", "time", "cravings"],
    coaching: { style: "check_ins", contact: "Messages, two video sessions a month" },
    targets: [
      { metric: "sit_to_stand", label: "Sit-to-stand (30 s)", baseline: 11, target: 15, by: "week 12" },
      { metric: "waist_cm", label: "Waist", baseline: 104, target: 98, by: "week 16" },
      { metric: "steps", label: "Average daily steps", baseline: 5200, target: 8000, by: "week 10" },
    ],
  };
  const bp2 = { ...bp1, schedule: { ...bp1.schedule, daysPerWeek: 3, minutesPerSession: 40 }, sleep: { hours: 6.8, notes: "Fixed 6:30 wake time since week 4" } };
  P.prepare("INSERT INTO blueprints (user_id, version, data_json, source, author, created_at) VALUES (?,?,?,?,?,?)").run(member, 1, JSON.stringify(bp1), "assessment", "Assessment + Blueprint session", ago(68));
  P.prepare("INSERT INTO blueprints (user_id, version, data_json, source, author, created_at) VALUES (?,?,?,?,?,?)").run(member, 2, JSON.stringify(bp2), "coach", "Riley Morgan (coach)", ago(28));

  // Measurements (demo data)
  const m = P.prepare("INSERT INTO measurements (user_id, metric, value, unit, source, measured_at) VALUES (?,?,?,?,?,?)");
  const weights = [92.4, 92.0, 91.6, 91.9, 91.1, 90.6, 90.8, 90.1, 89.7, 89.4];
  weights.forEach((w, i) => m.run(member, "weight_kg", w, "kg", "self", ago(70 - i * 7)));
  [104, 103, 101.5, 100.5, 99.5].forEach((w, i) => m.run(member, "waist_cm", w, "cm", "self", ago(70 - i * 14)));
  [11, 13, 14].forEach((v, i) => m.run(member, "sit_to_stand", v, "reps", "coach", ago(68 - i * 28)));
  [5200, 5600, 6300, 6900, 7100, 7400].forEach((v, i) => m.run(member, "steps", v, "steps/day", "self", ago(70 - i * 12)));
  [6.1, 6.4, 6.7, 6.8, 7.0].forEach((v, i) => m.run(member, "sleep_h", v, "h/night", "self", ago(70 - i * 14)));
  m.run(member, "lean_mass_kg", 58.1, "kg", "partner_scan", ago(66));
  m.run(member, "lean_mass_kg", 58.4, "kg", "partner_scan", ago(10));
  m.run(member, "body_fat_pct", 36.4, "%", "partner_scan", ago(66));
  m.run(member, "body_fat_pct", 34.6, "%", "partner_scan", ago(10));

  // This week's plan
  const wk = mondayOfThisWeek();
  const pi = P.prepare("INSERT INTO plan_items (user_id, week_start, day, kind, title, detail, video_id, done_at) VALUES (?,?,?,?,?,?,?,?)");
  pi.run(member, wk, 0, "training", "Strength A — 40 min", "Goblet squat 3×10 · Incline push-up 3×10 · Dowel hinge 3×12 · Carry 3×30 m", "goblet-squat", ago(0.5));
  pi.run(member, wk, 1, "habit", "Walk 30 minutes", "Aim for 7,500 steps today", null, null);
  pi.run(member, wk, 2, "lesson", "Lesson 2: Sleep and appetite", "8-minute lesson", "sleep-appetite", null);
  pi.run(member, wk, 3, "training", "Strength B — 40 min", "Box squat 3×8 · Incline push-up 3×12 · Hip hinge drill 3×12", "hip-hinge", null);
  pi.run(member, wk, 4, "nutrition", "Protein at breakfast", "Five breakfasts this week with a palm-sized protein portion", "protein-basics", null);
  pi.run(member, wk, 5, "training", "Partner session", "Open gym at [Partner gym] — your coach has loaded the session", null, null);
  pi.run(member, wk, 6, "test", "Weekly check-in", "Weigh-in, waist, and a 2-line note to your coach", "sit-to-stand", null);

  // Video progress
  const vp = P.prepare("INSERT INTO video_progress (user_id, video_id, position_s, duration_s, completed_at, saved, updated_at) VALUES (?,?,?,?,?,?,?)");
  vp.run(member, "how-it-works", 40, 40, ago(69), 0, ago(69));
  vp.run(member, "goblet-squat", 30, 30, ago(60), 1, ago(1));
  vp.run(member, "protein-basics", 40, 40, ago(40), 0, ago(40));
  vp.run(member, "hip-hinge", 12, 30, null, 0, ago(2));
  vp.run(member, "plateaus", 0, 40, null, 1, ago(5));

  // Coaching messages
  const msg = P.prepare("INSERT INTO messages (user_id, sender_id, sender_role, sender_name, body, created_at) VALUES (?,?,?,?,?,?)");
  msg.run(member, ids.coach, "coach", "Riley Morgan", "Welcome, Jordan! Your Blueprint is live. Start with Strength A on Monday — the goblet squat video is linked in your plan.", ago(67));
  msg.run(member, member, "member", "Jordan Lee", "Did Strength A. Knee felt fine on the box squat but not the full squat.", ago(9));
  msg.run(member, ids.coach, "coach", "Riley Morgan", "Good call stopping there. I've switched you to box squats for two weeks and we'll re-test depth after. Your sit-to-stand went from 11 to 14 — nice work.", ago(9, 14));

  // Sponsors, settings
  P.prepare("INSERT INTO sponsors (code, org_name, plan_id, seats) VALUES (?,?,?,?)").run("DEMO-EMPLOYER", "Example Employer Inc. (demo)", "core", 50);
  P.prepare("INSERT INTO settings (key, value) VALUES ('price_variant', '0')").run();

  // ── Clinical store (independent practice) ──
  C.prepare("INSERT INTO clinicians (id, name, designation, college, reg_no, licensed_provinces) VALUES (?,?,?,?,?,?)").run(
    ids.clinician, "Dr. Avery Demo", "MD", "CPSO", "[CPSO # placeholder]", "ON",
  );
  C.prepare("INSERT INTO patients (patient_ref, legal_name, dob, province, hcn_masked, created_at) VALUES (?,?,?,?,?,?)").run(patientRef, "Jordan Lee", "1984-03-14", "ON", "•••• ••• 4821", ago(56));
  C.prepare("INSERT INTO enrolments (patient_ref, status, privacy_notice_sha, virtual_care_consent_sha, enrolled_at) VALUES (?,?,?,?,?)").run(
    patientRef, "active", sha256(CLINICAL_ACKS.privacy_notice), sha256(CLINICAL_ACKS.virtual_care), ago(56),
  );
  C.prepare("INSERT INTO intake (patient_ref, answers_json, red_flags_json, submitted_at) VALUES (?,?,?,?)").run(
    patientRef, JSON.stringify({ demo: "Intake answers (demo)" }), JSON.stringify({ urgent: [], review: [] }), ago(56),
  );
  const enc = C.prepare("INSERT INTO encounters (id, patient_ref, clinician_id, kind, modality, starts_at, status, insured_status, fee_cents, location_attested, note, signed_at) VALUES (?,?,?,?,?,?,?,?,?,1,?,?)");
  const enc1 = newId("enc"), enc2 = newId("enc");
  enc.run(enc1, patientRef, ids.clinician, "initial", "video", ago(50, 15), "completed", "ohip", 0, "Demo note: history reviewed; baseline labs ordered; lifestyle programme continued.", ago(50, 16));
  enc.run(enc2, patientRef, ids.clinician, "follow_up", "video", ago(5, 15), "completed", "ohip", 0, "Demo note: results reviewed with patient; shared decision; see prescription.", ago(5, 16));
  enc.run(newId("enc"), patientRef, ids.clinician, "follow_up", "video", ahead(23, 15), "booked", "ohip", 0, null, null);

  const fA = "frm_demo_a", fB = "frm_demo_b";
  const f = C.prepare("INSERT INTO formulary (id, din, display_name, hc_status, approved_indication, monitoring, evidence_ref, governance_approved_at, demo) VALUES (?,?,?,?,?,?,?,?,1)");
  f.run(fA, "DEMO0001", "Formulary item A (demo placeholder)", "marketed", "[Approved indication per Health Canada product monograph]", "[Monitoring per monograph and practice protocol]", "[Evidence register ID]", ago(80));
  f.run(fB, "DEMO0002", "Formulary item B (demo placeholder)", "marketed", "[Approved indication per Health Canada product monograph]", "[Monitoring per monograph and practice protocol]", "[Evidence register ID]", ago(80));
  C.prepare("INSERT INTO prescriptions (id, patient_ref, clinician_id, encounter_id, formulary_id, sig, quantity, refills, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)").run(
    "rx_demo_1", patientRef, ids.clinician, enc2, fA, "[Directions as written by prescriber]", "[Quantity — 4-week supply]", 2, "active", ago(5, 16),
  );
  C.prepare("INSERT INTO labs (id, patient_ref, panel, status, ordered_at, resulted_at, result_summary, clinician_comment) VALUES (?,?,?,?,?,?,?,?)").run(
    newId("lab"), patientRef, "Baseline metabolic panel (demo)", "resulted", ago(50), ago(46), "Demo result summary — values would appear here from the lab feed.", "Reviewed — discussed at follow-up.",
  );
  C.prepare("INSERT INTO labs (id, patient_ref, panel, status, ordered_at) VALUES (?,?,?,?,?)").run(newId("lab"), patientRef, "12-week follow-up panel (demo)", "requisition_issued", ago(5));
  C.prepare("INSERT INTO clinical_messages (patient_ref, sender, sender_name, body, created_at) VALUES (?,?,?,?,?)").run(
    patientRef, "clinician", "Dr. Avery Demo", "As discussed, your prescription is ready. Choose where you'd like to fill it in Care → Prescriptions. Message me here if you have questions — for anything urgent call 911.", ago(5, 17),
  );
  C.prepare("INSERT INTO care_team_summaries (patient_ref, coach_safe_text, author_id, created_at) VALUES (?,?,?,?)").run(
    patientRef, "Cleared for progressive strength training. Avoid high-impact jumping for now (knee). No other restrictions.", ids.clinician, ago(50, 17),
  );
  audit("clinical", { actorId: ids.clinician, actorRole: "clinician", subjectUser: patientRef, action: "chart.viewed", resource: patientRef });
  audit("clinical", { actorId: ids.clinician, actorRole: "clinician", subjectUser: patientRef, action: "rx.issued", resource: "rx_demo_1" });

  // ── Pharmacy store ──
  const pl = R.prepare("INSERT INTO price_list (din, pack_desc, drug_cost_cents, dispensing_fee_cents, delivery_cents, cold_chain, demo) VALUES (?,?,?,?,?,?,1)");
  pl.run("DEMO0001", "4-week supply (demo)", 18900, 1299, 1500, 1);
  pl.run("DEMO0002", "30-day supply (demo)", 7400, 1299, 0, 0);

  // ── Synthetic demand-test data (tagged) ──
  const rand = rng(42);
  const ev = P.prepare("INSERT INTO events (anon_id, name, props_json, created_at) VALUES (?,?,?,?)");
  const plans = ["foundation", "core", "core", "core", "hybrid", "hybrid", "premium"];
  const juris = ["ON", "ON", "ON", "ON", "ON", "ON", "BC", "AB", "QC", "NS", "US"];
  for (let i = 0; i < 320; i++) {
    const anon = `synthetic-${i}`;
    const t = iso(rand() * 28 * day);
    const variant = rand() < 0.5 ? 0 : 1;
    const j = juris[Math.floor(rand() * juris.length)];
    const s = { source: "synthetic", variant, jurisdiction: j };
    ev.run(anon, "assessment_started", JSON.stringify(s), t);
    if (rand() > 0.62) continue;
    const plan = plans[Math.floor(rand() * plans.length)];
    const med = rand() < 0.46 ? "yes" : rand() < 0.5 ? "maybe" : "no";
    ev.run(anon, "assessment_completed", JSON.stringify(s), t);
    ev.run(anon, "path_suggested", JSON.stringify({ ...s, plan, medical_interest: med }), t);
    if (j !== "ON") {
      if (rand() < 0.5) ev.run(anon, "waitlist_joined", JSON.stringify(s), t);
      continue;
    }
    if (rand() < 0.08) ev.run(anon, "fake_door_clicked", JSON.stringify({ ...s, door: "employer" }), t);
    if (rand() > 0.45) continue;
    ev.run(anon, "join_started", JSON.stringify({ ...s, plan }), t);
    if (rand() > 0.7) continue;
    ev.run(anon, "account_created", JSON.stringify({ ...s, plan }), t);
    ev.run(anon, "order_review_viewed", JSON.stringify({ ...s, plan }), t);
    const payP = variant === 0 ? 0.62 : 0.48;
    if (rand() < payP) ev.run(anon, "order_paid", JSON.stringify({ ...s, plan }), t);
  }
  const wtp = P.prepare("INSERT INTO wtp_responses (anon_id, too_cheap, cheap, expensive, too_expensive, created_at) VALUES (?,?,?,?,?,?)");
  for (let i = 0; i < 48; i++) {
    const tc = Math.round((25 + rand() * 40) / 5) * 5;
    const ch = tc + Math.round((30 + rand() * 50) / 5) * 5;
    const ex = ch + Math.round((40 + rand() * 90) / 5) * 5;
    const tx = ex + Math.round((40 + rand() * 120) / 5) * 5;
    wtp.run(`synthetic-wtp-${i}`, tc, ch, ex, tx, iso(rand() * 28 * day));
  }
  const wl = P.prepare("INSERT INTO waitlist (email, jurisdiction, fsa, interests_json, marketing_consent, created_at) VALUES (?,?,?,?,?,?)");
  const wlj: Array<[string, string]> = [["BC", "V5K"], ["BC", "V6B"], ["AB", "T2P"], ["AB", "T5J"], ["QC", "H2X"], ["NS", "B3H"], ["MB", "R3C"], ["US", "NY"], ["US", "WA"], ["US", "FL"]];
  for (let i = 0; i < 36; i++) {
    const [j, fsa] = wlj[Math.floor(rand() * wlj.length)];
    wl.run(`synthetic+${i}@example.test`, j, fsa, JSON.stringify(rand() < 0.5 ? ["coaching", "medical"] : ["coaching"]), rand() < 0.6 ? 1 : 0, iso(rand() * 28 * day));
  }
  const ld = P.prepare("INSERT INTO leads (kind, org, name, email, size, message, created_at) VALUES (?,?,?,?,?,?,?)");
  ld.run("employer", "Synthetic Manufacturing Co.", "HR lead (synthetic)", "hr@example.test", "250-999", "Interested in a pilot for 40 employees.", iso(9 * day));
  ld.run("employer", "Synthetic Logistics Ltd.", "Benefits manager (synthetic)", "benefits@example.test", "1000+", "Want aggregate outcome reporting details.", iso(4 * day));
  ld.run("partner", "Synthetic Strength Studio", "Owner (synthetic)", "owner@example.test", "1-10", "Have off-peak capacity mornings.", iso(6 * day));
  ld.run("enterprise", "Synthetic Physio Group", "Director (synthetic)", "director@example.test", "50-249", "Licensing the Blueprint for our clinics?", iso(2 * day));
}
