import "server-only";
import { db, audit, newId, nowIso } from "@/lib/db";
import type { User } from "@/lib/auth";

/**
 * Access layer for the licensed pharmacy (separate legal entity, its own PHIPA custodian
 * and merchant of record for medication). Only prescriptions a patient chose to send
 * here arrive in its inbox.
 *
 * Anti-inducement by construction: pharmacyQuote() takes the product, quantity and drug-plan
 * coverage — it has no parameter through which membership tier, coaching purchases or
 * anything else on the platform could change a medication price.
 */
const P = () => db("pharmacy");

export function receivePrescription(rx: {
  prescriptionId: string; patientRef: string; legalName: string; dob: string; din: string; displayName: string; sig: string; quantity: string; refills: number;
}) {
  P().prepare("INSERT OR IGNORE INTO patients (patient_ref, legal_name, dob) VALUES (?,?,?)").run(rx.patientRef, rx.legalName, rx.dob);
  const id = newId("prx");
  P().prepare(
    "INSERT INTO rx_inbox (id, prescription_id, patient_ref, din, display_name, sig, quantity, refills_authorised, received_at) VALUES (?,?,?,?,?,?,?,?,?)",
  ).run(id, rx.prescriptionId, rx.patientRef, rx.din, rx.displayName, rx.sig, rx.quantity, rx.refills, nowIso());
  audit("pharmacy", { actorRole: "system", subjectUser: rx.patientRef, action: "rx.received", resource: id });
  return id;
}

export interface Quote {
  drugCents: number;
  dispensingFeeCents: number;
  deliveryCents: number;
  planPaysCents: number;
  patientTotalCents: number;
  coldChain: boolean;
}

export function pharmacyQuote(din: string, coverage: { planPaysPct: number }): Quote {
  const p = P().prepare("SELECT * FROM price_list WHERE din = ?").get(din) as
    | { drug_cost_cents: number; dispensing_fee_cents: number; delivery_cents: number; cold_chain: number }
    | undefined;
  if (!p) throw new Error("No price on file for this product");
  const eligible = p.drug_cost_cents + p.dispensing_fee_cents;
  const planPays = Math.round((eligible * Math.max(0, Math.min(100, coverage.planPaysPct))) / 100);
  return {
    drugCents: p.drug_cost_cents,
    dispensingFeeCents: p.dispensing_fee_cents,
    deliveryCents: p.delivery_cents,
    planPaysCents: planPays,
    patientTotalCents: eligible - planPays + p.delivery_cents,
    coldChain: p.cold_chain === 1,
  };
}

export interface FillRow {
  id: string; rx_id: string; status: string; display_name: string; sig: string; quantity: string; refills_authorised: number;
  patient_total_cents: number | null; plan_pays_cents: number; drug_cents: number | null; dispensing_fee_cents: number | null; delivery_cents: number | null;
  insurance_status: string; tracking: string | null; requested_at: string; paid_at: string | null; shipped_at: string | null; counselled_at: string | null; prescription_id: string;
}

export function patientPharmacyView(user: User) {
  if (user.role !== "member" || !user.patient_ref) throw new Error("Forbidden");
  const ref = user.patient_ref;
  const inbox = P().prepare("SELECT * FROM rx_inbox WHERE patient_ref = ? ORDER BY received_at DESC").all(ref) as Array<{
    id: string; prescription_id: string; display_name: string; sig: string; quantity: string; refills_authorised: number; received_at: string;
  }>;
  const fills = P().prepare(
    `SELECT f.*, r.display_name, r.sig, r.quantity, r.refills_authorised, r.prescription_id FROM fills f JOIN rx_inbox r ON r.id = f.rx_id
     WHERE f.patient_ref = ? ORDER BY f.requested_at DESC`,
  ).all(ref) as unknown as FillRow[];
  return { inbox, fills };
}

export function fillsUsed(rxId: string): number {
  return (P().prepare("SELECT COUNT(*) AS n FROM fills WHERE rx_id = ? AND status <> 'cancelled'").get(rxId) as { n: number }).n;
}

export function requestFill(user: User, rxId: string) {
  if (user.role !== "member" || !user.patient_ref) throw new Error("Forbidden");
  const rx = P().prepare("SELECT * FROM rx_inbox WHERE id = ? AND patient_ref = ?").get(rxId, user.patient_ref) as { refills_authorised: number } | undefined;
  if (!rx) throw new Error("Prescription not found at this pharmacy");
  const open = P().prepare("SELECT COUNT(*) AS n FROM fills WHERE rx_id = ? AND status IN ('requested','verified','awaiting_payment','paid')").get(rxId) as { n: number };
  if (open.n > 0) throw new Error("There is already a fill in progress for this prescription.");
  if (fillsUsed(rxId) > rx.refills_authorised) throw new Error("No refills remain. Ask your clinician whether to renew.");
  const id = newId("fill");
  P().prepare("INSERT INTO fills (id, rx_id, patient_ref, status, requested_at) VALUES (?,?,?,?,?)").run(id, rxId, user.patient_ref, "requested", nowIso());
  audit("pharmacy", { actorId: user.id, actorRole: "member", subjectUser: user.patient_ref, action: "fill.requested", resource: id });
  return id;
}

/** Mock payment to the PHARMACY as merchant of record (zero-rated; no platform involvement). */
export function payFill(user: User, fillId: string) {
  if (user.role !== "member" || !user.patient_ref) throw new Error("Forbidden");
  const f = P().prepare("SELECT * FROM fills WHERE id = ? AND patient_ref = ?").get(fillId, user.patient_ref) as { status: string; patient_total_cents: number } | undefined;
  if (!f || f.status !== "awaiting_payment") throw new Error("This fill is not awaiting payment");
  P().prepare("UPDATE fills SET status = 'paid', paid_at = ? WHERE id = ?").run(nowIso(), fillId);
  P().prepare("INSERT INTO orders (id, fill_id, patient_ref, total_cents, status) VALUES (?,?,?,?, 'paid')").run(newId("pord"), fillId, user.patient_ref, f.patient_total_cents);
  audit("pharmacy", { actorId: user.id, actorRole: "member", subjectUser: user.patient_ref, action: "fill.paid", resource: fillId });
}

// ── Pharmacist-facing ──────────────────────────────────────────────────────

function assertPharmacist(user: User) {
  if (user.role !== "pharmacist") throw new Error("Forbidden: pharmacists only");
}

export function pharmacistQueue(user: User) {
  assertPharmacist(user);
  audit("pharmacy", { actorId: user.id, actorRole: "pharmacist", action: "queue.viewed" });
  return P().prepare(
    `SELECT f.*, r.display_name, r.din, r.sig, r.quantity, r.refills_authorised, p.legal_name
     FROM fills f JOIN rx_inbox r ON r.id = f.rx_id JOIN patients p ON p.patient_ref = f.patient_ref
     ORDER BY CASE f.status WHEN 'requested' THEN 0 WHEN 'paid' THEN 1 WHEN 'awaiting_payment' THEN 2 ELSE 3 END, f.requested_at DESC`,
  ).all() as unknown as Array<FillRow & { din: string; legal_name: string }>;
}

export function pharmacistVerify(user: User, fillId: string, input: { counselled: boolean; planPaysPct: number }) {
  assertPharmacist(user);
  const f = P().prepare("SELECT f.*, r.din FROM fills f JOIN rx_inbox r ON r.id = f.rx_id WHERE f.id = ?").get(fillId) as { status: string; din: string; patient_ref: string; rx_id: string } | undefined;
  if (!f || f.status !== "requested") throw new Error("Fill is not awaiting verification");
  const firstFill = (P().prepare("SELECT COUNT(*) AS n FROM fills WHERE rx_id = ? AND counselled_at IS NOT NULL").get(f.rx_id) as { n: number }).n === 0;
  if (firstFill && !input.counselled) throw new Error("A first fill requires pharmacist counselling before release.");
  const q = pharmacyQuote(f.din, { planPaysPct: input.planPaysPct });
  P().prepare(
    `UPDATE fills SET status = 'awaiting_payment', pharmacist_id = ?, counselled_at = COALESCE(?, counselled_at), insurance_status = ?,
       drug_cents = ?, dispensing_fee_cents = ?, delivery_cents = ?, plan_pays_cents = ?, patient_total_cents = ? WHERE id = ?`,
  ).run(user.id, input.counselled ? nowIso() : null, input.planPaysPct > 0 ? "adjudicated" : "cash", q.drugCents, q.dispensingFeeCents, q.deliveryCents, q.planPaysCents, q.patientTotalCents, fillId);
  audit("pharmacy", { actorId: user.id, actorRole: "pharmacist", subjectUser: f.patient_ref, action: "fill.verified", resource: fillId });
}

export function pharmacistShip(user: User, fillId: string, tracking: string) {
  assertPharmacist(user);
  const f = P().prepare("SELECT status, patient_ref FROM fills WHERE id = ?").get(fillId) as { status: string; patient_ref: string } | undefined;
  if (!f || f.status !== "paid") throw new Error("Only paid fills can be shipped");
  P().prepare("UPDATE fills SET status = 'shipped', tracking = ?, shipped_at = ? WHERE id = ?").run(tracking, nowIso(), fillId);
  audit("pharmacy", { actorId: user.id, actorRole: "pharmacist", subjectUser: f.patient_ref, action: "fill.shipped", resource: fillId });
}

export function pharmacyRevenueSummary() {
  // Aggregate only — reported by the pharmacy entity, never per clinician.
  return P().prepare("SELECT COUNT(*) AS orders, COALESCE(SUM(total_cents),0) AS patient_paid_cents FROM orders WHERE status = 'paid'").get() as { orders: number; patient_paid_cents: number };
}
