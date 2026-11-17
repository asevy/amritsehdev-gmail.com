"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireUser } from "@/lib/auth";
import { db, nowIso } from "@/lib/db";
import { clinicianCompleteEncounter, clinicianPrescribe, clinicianReply, clinicianWriteSummary } from "@/lib/clinical";
import { pharmacistVerify, pharmacistShip } from "@/lib/pharmacy";
import { setSetting } from "@/lib/db";

// ── Clinician (independent practice) ──
export async function signEncounter(form: FormData) {
  const u = await requireUser(["clinician"]);
  clinicianCompleteEncounter(u, String(form.get("encounterId")), String(form.get("note") ?? "").slice(0, 4000));
  revalidatePath("/staff/clinician");
}

export async function prescribe(form: FormData) {
  const u = await requireUser(["clinician"]);
  const ref = String(form.get("patientRef"));
  try {
    clinicianPrescribe(u, {
      patientRef: ref,
      formularyId: String(form.get("formularyId")),
      sig: String(form.get("sig") ?? "").slice(0, 300) || "[Directions]",
      quantity: String(form.get("quantity") ?? "").slice(0, 100) || "[Quantity]",
      refills: Math.max(0, Math.min(11, Number(form.get("refills")) || 0)),
    });
  } catch (e) {
    redirect(`/staff/clinician?p=${ref}&error=${encodeURIComponent((e as Error).message)}`);
  }
  revalidatePath("/staff/clinician");
  redirect(`/staff/clinician?p=${ref}&rx=1`);
}

export async function clinicianMessage(form: FormData) {
  const u = await requireUser(["clinician"]);
  const ref = String(form.get("patientRef"));
  const body = String(form.get("body") ?? "").trim();
  if (body) clinicianReply(u, ref, body.slice(0, 4000));
  revalidatePath("/staff/clinician");
  redirect(`/staff/clinician?p=${ref}`);
}

export async function writeCareSummary(form: FormData) {
  const u = await requireUser(["clinician"]);
  const ref = String(form.get("patientRef"));
  const text = String(form.get("text") ?? "").trim();
  if (text) clinicianWriteSummary(u, ref, text.slice(0, 600));
  revalidatePath("/staff/clinician");
  redirect(`/staff/clinician?p=${ref}`);
}

// ── Pharmacist (licensed pharmacy) ──
export async function verifyFill(form: FormData) {
  const u = await requireUser(["pharmacist"]);
  try {
    pharmacistVerify(u, String(form.get("fillId")), { counselled: form.get("counselled") === "on", planPaysPct: Number(form.get("planPaysPct")) || 0 });
  } catch (e) {
    redirect(`/staff/pharmacy?error=${encodeURIComponent((e as Error).message)}`);
  }
  revalidatePath("/staff/pharmacy");
}

export async function shipFill(form: FormData) {
  const u = await requireUser(["pharmacist"]);
  try {
    pharmacistShip(u, String(form.get("fillId")), `DEMO-${Math.random().toString(36).slice(2, 10).toUpperCase()}`);
  } catch (e) {
    redirect(`/staff/pharmacy?error=${encodeURIComponent((e as Error).message)}`);
  }
  revalidatePath("/staff/pharmacy");
}

// ── Coach (platform) ──
export async function coachReply(form: FormData) {
  const u = await requireUser(["coach"]);
  const memberId = String(form.get("memberId"));
  const body = String(form.get("body") ?? "").trim().slice(0, 4000);
  if (body) db("platform").prepare("INSERT INTO messages (user_id, sender_id, sender_role, sender_name, body, created_at) VALUES (?,?,?,?,?,?)").run(memberId, u.id, "coach", u.name, body, nowIso());
  revalidatePath("/staff/coach");
  redirect(`/staff/coach?m=${memberId}`);
}

// ── Admin (founders) ──
export async function setPriceVariant(form: FormData) {
  await requireUser(["admin"]);
  setSetting("price_variant", form.get("variant") === "1" ? "1" : "0");
  revalidatePath("/admin");
}
