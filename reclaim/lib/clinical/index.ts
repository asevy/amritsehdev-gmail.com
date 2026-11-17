import "server-only";
import { db, audit, newId, nowIso, sha256 } from "@/lib/db";
import { CLINICAL_ACKS } from "@/config/consents";
import { receivePrescription } from "@/lib/pharmacy";
import { PHARMACY_OPTIONS, type PharmacyChoice } from "@/config/partners";
import type { User } from "@/lib/auth";

/**
 * Access layer for the independent medical practice's record (PHIPA custodian).
 * The platform acts only as the practice's agent / electronic service provider.
 * - Members can read their own record.
 * - Clinicians can read and write any record of the practice.
 * - Coaches, pharmacists and platform admins/founders have NO access here.
 *   (Coaches see only care_team_summaries, and only with the patient's consent.)
 */
const C = () => db("clinical");

function assertMemberOwns(user: User, patientRef: string) {
  if (user.role !== "member" || user.patient_ref !== patientRef) throw new Error("Forbidden: not your record");
}
function assertClinician(user: User) {
  if (user.role !== "clinician") throw new Error("Forbidden: clinicians only");
}

export interface Prescription {
  id: string;
  formulary_id: string;
  display_name: string;
  sig: string;
  quantity: string;
  refills: number;
  status: string;
  destination_type: PharmacyChoice | null;
  destination_detail: string | null;
  choice_made_at: string | null;
  created_at: string;
  monitoring: string;
  clinician_name: string;
}

// ── Member-facing ──────────────────────────────────────────────────────────

export function getEnrolment(user: User) {
  if (!user.patient_ref) return null;
  return (C().prepare("SELECT * FROM enrolments WHERE patient_ref = ?").get(user.patient_ref) as
    | { status: string; enrolled_at: string }
    | undefined) ?? null;
}

/** Red-flag rules. CLINICAL CONTENT PLACEHOLDER — to be authored and approved by the medical director. */
export function intakeRedFlags(a: Record<string, string>): { urgent: string[]; review: string[] } {
  const urgent: string[] = [];
  const review: string[] = [];
  if (a.current_symptoms === "yes") urgent.push("Reported chest pain, fainting or severe shortness of breath");
  if (a.pregnancy === "yes") review.push("Pregnant, breastfeeding or planning pregnancy");
  if (a.eating_disorder === "yes") review.push("History of an eating disorder");
  if (a.thyroid_history === "yes") review.push("Personal/family history of medullary thyroid cancer or MEN2");
  if (a.pancreatitis === "yes") review.push("History of pancreatitis");
  if (a.diabetes_type === "type1") review.push("Type 1 diabetes");
  if (a.age_band === "under18") urgent.push("Under 18 — not eligible for this service");
  return { urgent, review };
}

export function enrolAndSubmitIntake(user: User, answers: Record<string, string>, legal: { legalName: string; dob: string; hcnLast4: string }) {
  if (user.role !== "member" || !user.patient_ref) throw new Error("Forbidden");
  const flags = intakeRedFlags(answers);
  const ref = user.patient_ref;
  C().prepare("INSERT OR IGNORE INTO patients (patient_ref, legal_name, dob, province, hcn_masked) VALUES (?,?,?,?,?)")
    .run(ref, legal.legalName, legal.dob, user.province ?? "ON", legal.hcnLast4 ? `•••• ••• ${legal.hcnLast4}` : null);
  C().prepare(
    "INSERT INTO enrolments (patient_ref, status, privacy_notice_sha, virtual_care_consent_sha) VALUES (?,?,?,?) ON CONFLICT(patient_ref) DO UPDATE SET status = excluded.status",
  ).run(ref, "intake_submitted", sha256(CLINICAL_ACKS.privacy_notice), sha256(CLINICAL_ACKS.virtual_care));
  C().prepare("INSERT INTO intake (patient_ref, answers_json, red_flags_json) VALUES (?,?,?)").run(ref, JSON.stringify(answers), JSON.stringify(flags));
  audit("clinical", { actorId: user.id, actorRole: "member", subjectUser: ref, action: "intake.submitted", resource: "intake" });
  return flags;
}

export function listEncounters(user: User) {
  assertMemberOwns(user, user.patient_ref!);
  return C().prepare(
    `SELECT e.*, c.name AS clinician_name, c.designation FROM encounters e JOIN clinicians c ON c.id = e.clinician_id
     WHERE patient_ref = ? ORDER BY starts_at DESC`,
  ).all(user.patient_ref) as Array<{ id: string; kind: string; modality: string; starts_at: string; status: string; insured_status: string; fee_cents: number; clinician_name: string; designation: string }>;
}

export function bookEncounter(user: User, input: { startsAt: string; modality: "video" | "phone"; locationAttested: boolean }) {
  assertMemberOwns(user, user.patient_ref!);
  if (!input.locationAttested) throw new Error("You must confirm you will be in Ontario at the time of the visit.");
  const province = user.province ?? "ON";
  // Licensure check: only clinicians licensed where the patient will be located.
  const clinician = (C().prepare("SELECT id, licensed_provinces FROM clinicians").all() as Array<{ id: string; licensed_provinces: string }>)
    .find((c) => c.licensed_provinces.split(",").includes(province));
  if (!clinician) throw new Error("No clinician licensed in your province is available.");
  const patient = C().prepare("SELECT hcn_masked FROM patients WHERE patient_ref = ?").get(user.patient_ref) as { hcn_masked: string | null } | undefined;
  const insured = patient?.hcn_masked ? "ohip" : "tbd";
  const prior = C().prepare("SELECT COUNT(*) AS n FROM encounters WHERE patient_ref = ? AND status = 'completed'").get(user.patient_ref) as { n: number };
  const id = newId("enc");
  C().prepare(
    "INSERT INTO encounters (id, patient_ref, clinician_id, kind, modality, starts_at, status, insured_status, fee_cents, location_attested) VALUES (?,?,?,?,?,?,?,?,0,1)",
  ).run(id, user.patient_ref, clinician.id, prior.n > 0 ? "follow_up" : "initial", input.modality, input.startsAt, "booked", insured);
  audit("clinical", { actorId: user.id, actorRole: "member", subjectUser: user.patient_ref, action: "encounter.booked", resource: id });
  return id;
}

export function cancelEncounter(user: User, id: string) {
  assertMemberOwns(user, user.patient_ref!);
  C().prepare("UPDATE encounters SET status = 'cancelled' WHERE id = ? AND patient_ref = ? AND status = 'booked'").run(id, user.patient_ref);
  audit("clinical", { actorId: user.id, actorRole: "member", subjectUser: user.patient_ref, action: "encounter.cancelled", resource: id });
}

export function listPrescriptions(user: User): Prescription[] {
  assertMemberOwns(user, user.patient_ref!);
  return C().prepare(
    `SELECT p.*, f.display_name, f.monitoring, c.name AS clinician_name FROM prescriptions p
     JOIN formulary f ON f.id = p.formulary_id JOIN clinicians c ON c.id = p.clinician_id
     WHERE p.patient_ref = ? ORDER BY p.created_at DESC`,
  ).all(user.patient_ref) as unknown as Prescription[];
}

/** Server-side shuffle so the aligned pharmacy has no positional advantage. */
export function presentPharmacyOptions(): PharmacyChoice[] {
  const ids = PHARMACY_OPTIONS.map((o) => o.id) as PharmacyChoice[];
  for (let i = ids.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  return ids;
}

export function choosePharmacy(user: User, rxId: string, choice: PharmacyChoice, detail: string, presented: string[]) {
  assertMemberOwns(user, user.patient_ref!);
  const rx = C().prepare(
    `SELECT p.*, f.din, f.display_name FROM prescriptions p JOIN formulary f ON f.id = p.formulary_id WHERE p.id = ? AND p.patient_ref = ?`,
  ).get(rxId, user.patient_ref) as (Prescription & { din: string; patient_ref: string }) | undefined;
  if (!rx) throw new Error("Prescription not found");
  if (rx.destination_type) throw new Error("A pharmacy has already been chosen for this prescription. Message your clinician to transfer it.");
  C().prepare(
    "UPDATE prescriptions SET destination_type = ?, destination_detail = ?, choice_presented_json = ?, choice_made_at = ? WHERE id = ?",
  ).run(choice, detail || null, JSON.stringify(presented), nowIso(), rxId);
  audit("clinical", { actorId: user.id, actorRole: "member", subjectUser: user.patient_ref, action: `rx.destination.${choice}`, resource: rxId });

  if (choice === "aligned_pharmacy") {
    const patient = C().prepare("SELECT legal_name, dob FROM patients WHERE patient_ref = ?").get(user.patient_ref) as { legal_name: string; dob: string };
    // Transmission to the pharmacy the patient chose (in production: e-prescribing network or secure fax).
    receivePrescription({
      prescriptionId: rx.id,
      patientRef: user.patient_ref!,
      legalName: patient.legal_name,
      dob: patient.dob,
      din: rx.din,
      displayName: rx.display_name,
      sig: rx.sig,
      quantity: rx.quantity,
      refills: rx.refills,
    });
  }
}

export function listLabs(user: User) {
  assertMemberOwns(user, user.patient_ref!);
  return C().prepare("SELECT * FROM labs WHERE patient_ref = ? ORDER BY ordered_at DESC").all(user.patient_ref) as Array<{
    id: string; panel: string; status: string; ordered_at: string; resulted_at: string | null; result_summary: string | null; clinician_comment: string | null;
  }>;
}

export function listClinicalMessages(user: User) {
  assertMemberOwns(user, user.patient_ref!);
  return C().prepare("SELECT * FROM clinical_messages WHERE patient_ref = ? ORDER BY id").all(user.patient_ref) as Array<{
    id: number; sender: string; sender_name: string; body: string; created_at: string;
  }>;
}

export function sendClinicalMessage(user: User, body: string) {
  assertMemberOwns(user, user.patient_ref!);
  C().prepare("INSERT INTO clinical_messages (patient_ref, sender, sender_name, body, created_at) VALUES (?,?,?,?,?)")
    .run(user.patient_ref, "patient", user.name, body, nowIso());
  audit("clinical", { actorId: user.id, actorRole: "member", subjectUser: user.patient_ref, action: "message.sent", resource: "clinical_messages" });
}

export function reportSideEffect(user: User, description: string, severity: "mild" | "moderate" | "severe") {
  assertMemberOwns(user, user.patient_ref!);
  C().prepare("INSERT INTO side_effect_reports (patient_ref, description, severity, created_at) VALUES (?,?,?,?)").run(user.patient_ref, description, severity, nowIso());
  audit("clinical", { actorId: user.id, actorRole: "member", subjectUser: user.patient_ref, action: "side_effect.reported", resource: severity });
}

/** Who has accessed this patient's clinical record (excluding the patient's own actions). */
export function accessLog(user: User) {
  assertMemberOwns(user, user.patient_ref!);
  return C().prepare(
    "SELECT actor_role, action, resource, created_at FROM audit_log WHERE subject_user = ? AND actor_role <> 'member' ORDER BY id DESC LIMIT 50",
  ).all(user.patient_ref) as Array<{ actor_role: string; action: string; resource: string; created_at: string }>;
}

/** The only clinical content a coach may see; requires the patient's consent (checked by the caller). */
export function latestCareSummary(patientRef: string): { coach_safe_text: string; created_at: string } | null {
  return (C().prepare("SELECT coach_safe_text, created_at FROM care_team_summaries WHERE patient_ref = ? ORDER BY id DESC LIMIT 1").get(patientRef) as
    | { coach_safe_text: string; created_at: string }
    | undefined) ?? null;
}

export function exportClinicalSummaryForPatient(user: User) {
  assertMemberOwns(user, user.patient_ref!);
  const ref = user.patient_ref;
  return {
    note: "Copy of your record held by the independent medical practice. A complete copy (including clinical notes) is available through a formal access request to the practice.",
    encounters: C().prepare("SELECT kind, modality, starts_at, status, insured_status FROM encounters WHERE patient_ref = ?").all(ref),
    prescriptions: C().prepare("SELECT p.created_at, f.display_name, p.sig, p.quantity, p.refills, p.status, p.destination_type FROM prescriptions p JOIN formulary f ON f.id = p.formulary_id WHERE patient_ref = ?").all(ref),
    labs: C().prepare("SELECT panel, status, ordered_at, resulted_at, result_summary FROM labs WHERE patient_ref = ?").all(ref),
  };
}

// ── Clinician-facing ───────────────────────────────────────────────────────

export function clinicianQueue(user: User) {
  assertClinician(user);
  audit("clinical", { actorId: user.id, actorRole: "clinician", action: "queue.viewed" });
  return C().prepare(
    `SELECT p.patient_ref, p.legal_name, p.province, e.status AS enrolment,
       (SELECT red_flags_json FROM intake i WHERE i.patient_ref = p.patient_ref ORDER BY id DESC LIMIT 1) AS flags,
       (SELECT MIN(starts_at) FROM encounters x WHERE x.patient_ref = p.patient_ref AND x.status = 'booked') AS next_visit,
       (SELECT COUNT(*) FROM side_effect_reports s WHERE s.patient_ref = p.patient_ref AND s.status = 'new') AS new_reports,
       (SELECT COUNT(*) FROM clinical_messages m WHERE m.patient_ref = p.patient_ref AND m.sender = 'patient'
          AND m.id > COALESCE((SELECT MAX(id) FROM clinical_messages m2 WHERE m2.patient_ref = p.patient_ref AND m2.sender = 'clinician'), 0)) AS unanswered
     FROM patients p JOIN enrolments e ON e.patient_ref = p.patient_ref ORDER BY next_visit IS NULL, next_visit`,
  ).all() as Array<{ patient_ref: string; legal_name: string; province: string; enrolment: string; flags: string | null; next_visit: string | null; new_reports: number; unanswered: number }>;
}

export function clinicianChart(user: User, patientRef: string) {
  assertClinician(user);
  audit("clinical", { actorId: user.id, actorRole: "clinician", subjectUser: patientRef, action: "chart.viewed", resource: patientRef });
  const c = C();
  return {
    patient: c.prepare("SELECT * FROM patients WHERE patient_ref = ?").get(patientRef) as { legal_name: string; dob: string; province: string; hcn_masked: string | null } | undefined,
    intake: c.prepare("SELECT * FROM intake WHERE patient_ref = ? ORDER BY id DESC LIMIT 1").get(patientRef) as { answers_json: string; red_flags_json: string; submitted_at: string } | undefined,
    encounters: c.prepare("SELECT * FROM encounters WHERE patient_ref = ? ORDER BY starts_at DESC").all(patientRef) as Array<{ id: string; kind: string; starts_at: string; status: string; insured_status: string; note: string | null }>,
    prescriptions: c.prepare("SELECT p.*, f.display_name FROM prescriptions p JOIN formulary f ON f.id = p.formulary_id WHERE patient_ref = ? ORDER BY created_at DESC").all(patientRef) as Array<{ id: string; display_name: string; sig: string; destination_type: string | null; created_at: string; status: string }>,
    messages: c.prepare("SELECT * FROM clinical_messages WHERE patient_ref = ? ORDER BY id").all(patientRef) as Array<{ sender: string; sender_name: string; body: string; created_at: string }>,
    reports: c.prepare("SELECT * FROM side_effect_reports WHERE patient_ref = ? ORDER BY id DESC").all(patientRef) as Array<{ id: number; description: string; severity: string; status: string; created_at: string }>,
    summary: latestCareSummary(patientRef),
    formulary: c.prepare("SELECT * FROM formulary ORDER BY display_name").all() as Array<{ id: string; display_name: string; approved_indication: string; monitoring: string; demo: number }>,
  };
}

export function clinicianCompleteEncounter(user: User, encounterId: string, note: string) {
  assertClinician(user);
  const enc = C().prepare("SELECT patient_ref FROM encounters WHERE id = ?").get(encounterId) as { patient_ref: string } | undefined;
  if (!enc) throw new Error("Not found");
  C().prepare("UPDATE encounters SET status = 'completed', note = ?, signed_at = ? WHERE id = ?").run(note, nowIso(), encounterId);
  C().prepare("UPDATE enrolments SET status = 'active' WHERE patient_ref = ?").run(enc.patient_ref);
  audit("clinical", { actorId: user.id, actorRole: "clinician", subjectUser: enc.patient_ref, action: "encounter.signed", resource: encounterId });
}

export function clinicianPrescribe(user: User, input: { patientRef: string; formularyId: string; sig: string; quantity: string; refills: number }) {
  assertClinician(user);
  const f = C().prepare("SELECT id FROM formulary WHERE id = ?").get(input.formularyId);
  if (!f) throw new Error("Only formulary products approved by clinical governance can be prescribed here.");
  const id = newId("rx");
  C().prepare(
    "INSERT INTO prescriptions (id, patient_ref, clinician_id, formulary_id, sig, quantity, refills, status, created_at) VALUES (?,?,?,?,?,?,?,'active',?)",
  ).run(id, input.patientRef, user.id, input.formularyId, input.sig, input.quantity, input.refills, nowIso());
  audit("clinical", { actorId: user.id, actorRole: "clinician", subjectUser: input.patientRef, action: "rx.issued", resource: id });
  return id;
}

export function clinicianReply(user: User, patientRef: string, body: string) {
  assertClinician(user);
  C().prepare("INSERT INTO clinical_messages (patient_ref, sender, sender_name, body, created_at) VALUES (?,?,?,?,?)").run(patientRef, "clinician", user.name, body, nowIso());
  C().prepare("UPDATE side_effect_reports SET status = 'reviewed' WHERE patient_ref = ? AND status = 'new'").run(patientRef);
  audit("clinical", { actorId: user.id, actorRole: "clinician", subjectUser: patientRef, action: "message.sent", resource: "clinical_messages" });
}

export function clinicianWriteSummary(user: User, patientRef: string, text: string) {
  assertClinician(user);
  C().prepare("INSERT INTO care_team_summaries (patient_ref, coach_safe_text, author_id, created_at) VALUES (?,?,?,?)").run(patientRef, text, user.id, nowIso());
  audit("clinical", { actorId: user.id, actorRole: "clinician", subjectUser: patientRef, action: "care_summary.written" });
}
