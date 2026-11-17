"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireUser } from "@/lib/auth";
import { db, newId, nowIso, audit } from "@/lib/db";
import { recordConsent } from "@/lib/consent";
import { toggleSaved } from "@/lib/media-auth";
import { creditBalance, activeSubscription } from "@/lib/commerce";
import { partnerById, CREDIT_RULES } from "@/config/partners";
import { CONSENTS, type ConsentKind } from "@/config/consents";
import { sendEmail } from "@/lib/email";

async function member() {
  return requireUser(["member"]);
}
async function memberWithPlan() {
  const u = await member();
  if (!activeSubscription(u.id)) redirect("/programmes");
  return u;
}

export async function togglePlanItem(form: FormData) {
  const u = await memberWithPlan();
  db("platform").prepare("UPDATE plan_items SET done_at = CASE WHEN done_at IS NULL THEN ? ELSE NULL END WHERE id = ? AND user_id = ?").run(nowIso(), Number(form.get("id")), u.id);
  revalidatePath("/portal");
  revalidatePath("/portal/plan");
}

const METRICS: Record<string, { unit: string; min: number; max: number }> = {
  weight_kg: { unit: "kg", min: 25, max: 350 },
  waist_cm: { unit: "cm", min: 40, max: 250 },
  sit_to_stand: { unit: "reps", min: 0, max: 60 },
  steps: { unit: "steps/day", min: 0, max: 60000 },
  sleep_h: { unit: "h/night", min: 0, max: 16 },
};

export async function logMeasurement(form: FormData) {
  const u = await memberWithPlan();
  const metric = String(form.get("metric"));
  const value = Number(form.get("value"));
  const spec = METRICS[metric];
  if (!spec || !Number.isFinite(value) || value < spec.min || value > spec.max) redirect("/portal/progress?error=range");
  db("platform").prepare("INSERT INTO measurements (user_id, metric, value, unit, source, measured_at, note) VALUES (?,?,?,?,?,?,?)")
    .run(u.id, metric, value, spec.unit, "self", nowIso(), String(form.get("note") ?? "").slice(0, 200) || null);
  revalidatePath("/portal/progress");
  revalidatePath("/portal");
}

export async function sendCoachMessage(form: FormData) {
  const u = await memberWithPlan();
  const body = String(form.get("body") ?? "").trim().slice(0, 4000);
  if (!body) return;
  db("platform").prepare("INSERT INTO messages (user_id, sender_id, sender_role, sender_name, body, created_at) VALUES (?,?,?,?,?,?)").run(u.id, u.id, "member", u.name, body, nowIso());
  revalidatePath("/portal/messages");
}

export async function bookCoachSession(form: FormData) {
  const u = await memberWithPlan();
  const startsAt = String(form.get("startsAt"));
  const kind = String(form.get("type")) === "blueprint" ? "Blueprint session with your coach" : "Coach session (30 min)";
  if (Number.isNaN(Date.parse(startsAt)) || Date.parse(startsAt) < Date.now()) redirect("/portal/appointments?error=time");
  db("platform").prepare("INSERT INTO bookings (id, user_id, kind, title, starts_at, duration_min, status) VALUES (?,?,?,?,?,?,?)")
    .run(newId("bk"), u.id, "coach", kind, startsAt, kind.startsWith("Blueprint") ? 60 : 30, "booked");
  sendEmail({ to: u.email, userId: u.id, entity: "platform", kind: "transactional", subject: "Booking confirmed", body: `${kind} on ${new Date(startsAt).toLocaleString("en-CA", { timeZone: "America/Toronto" })}.` });
  revalidatePath("/portal/appointments");
  redirect("/portal/appointments?booked=1");
}

export async function bookPartnerSession(form: FormData) {
  const u = await memberWithPlan();
  const p = partnerById(String(form.get("partnerId")));
  const startsAt = String(form.get("startsAt"));
  if (!p || p.booking !== "credits" || !p.credits) redirect("/portal/network?error=partner");
  if (Number.isNaN(Date.parse(startsAt)) || Date.parse(startsAt) < Date.now()) redirect("/portal/network?error=time");
  if (creditBalance(u.id) < p.credits) redirect("/portal/network?error=credits");
  const id = newId("bk");
  const d = db("platform");
  d.prepare("INSERT INTO bookings (id, user_id, kind, partner_id, title, starts_at, duration_min, status, credits_used) VALUES (?,?,?,?,?,?,?,?,?)")
    .run(id, u.id, "partner", p.id, p.name, startsAt, p.sessionMinutes, "booked", p.credits);
  d.prepare("INSERT INTO credits_ledger (user_id, delta, reason, ref) VALUES (?,?,?,?)").run(u.id, -p.credits, `Booked: ${p.name}`, id);
  revalidatePath("/portal/network");
  redirect("/portal/network?booked=1");
}

export async function cancelBooking(form: FormData) {
  const u = await memberWithPlan();
  const id = String(form.get("id"));
  const d = db("platform");
  const b = d.prepare("SELECT * FROM bookings WHERE id = ? AND user_id = ? AND status = 'booked'").get(id, u.id) as { starts_at: string; credits_used: number; title: string } | undefined;
  if (!b) return;
  d.prepare("UPDATE bookings SET status = 'cancelled' WHERE id = ?").run(id);
  const hoursAhead = (Date.parse(b.starts_at) - Date.now()) / 3600_000;
  if (b.credits_used > 0 && hoursAhead >= CREDIT_RULES.freeCancelHours) {
    d.prepare("INSERT INTO credits_ledger (user_id, delta, reason, ref) VALUES (?,?,?,?)").run(u.id, b.credits_used, `Refunded: cancelled ${b.title}`, id);
  }
  revalidatePath("/portal/network");
  revalidatePath("/portal/appointments");
}

export async function toggleSaveVideo(form: FormData) {
  const u = await memberWithPlan();
  toggleSaved(u.id, String(form.get("videoId")));
  revalidatePath("/portal/library");
}

export async function updateBlueprintPreferences(form: FormData) {
  const u = await memberWithPlan();
  const d = db("platform");
  const latest = d.prepare("SELECT version, data_json FROM blueprints WHERE user_id = ? ORDER BY version DESC LIMIT 1").get(u.id) as { version: number; data_json: string } | undefined;
  const data = latest ? JSON.parse(latest.data_json) : {};
  data.schedule = { ...(data.schedule ?? {}), daysPerWeek: Number(form.get("daysPerWeek")) || data.schedule?.daysPerWeek, minutesPerSession: Number(form.get("minutesPerSession")) || data.schedule?.minutesPerSession, bestTimes: String(form.get("bestTimes") ?? "") };
  data.painLimitations = String(form.get("painLimitations") ?? "").slice(0, 500);
  data.nutrition = { ...(data.nutrition ?? {}), notes: String(form.get("nutritionNotes") ?? "").slice(0, 500) };
  data.coaching = { ...(data.coaching ?? {}), contact: String(form.get("coachingContact") ?? "").slice(0, 200) };
  d.prepare("INSERT INTO blueprints (user_id, version, data_json, source, author) VALUES (?,?,?,?,?)").run(u.id, (latest?.version ?? 0) + 1, JSON.stringify(data), "member", `${u.name} (member)`);
  revalidatePath("/portal/blueprint");
  redirect("/portal/blueprint?saved=1");
}

export async function setConsent(form: FormData) {
  const u = await member();
  const kind = String(form.get("kind")) as ConsentKind;
  const def = CONSENTS[kind];
  if (!def || !def.withdrawable) return;
  recordConsent(u.id, kind, form.get("granted") === "1", "/portal/privacy");
  audit("platform", { actorId: u.id, actorRole: "member", subjectUser: u.id, action: `consent.${kind}.${form.get("granted") === "1" ? "granted" : "withdrawn"}` });
  revalidatePath("/portal/privacy");
}

export async function requestDataAction(form: FormData) {
  const u = await member();
  const kind = String(form.get("kind"));
  const entity = String(form.get("entity"));
  if (!["deletion", "correction", "access"].includes(kind) || !["platform", "clinical"].includes(entity)) return;
  const due = new Date(Date.now() + 30 * 86400_000).toISOString();
  db("platform").prepare("INSERT INTO data_requests (user_id, entity_id, kind, due_at) VALUES (?,?,?,?)").run(u.id, entity, kind, due);
  sendEmail({ to: u.email, userId: u.id, entity: entity === "clinical" ? "clinical" : "platform", kind: "transactional", subject: `We received your ${kind} request`, body: `We'll respond by ${due.slice(0, 10)}.` });
  revalidatePath("/portal/privacy");
  redirect("/portal/privacy?requested=1");
}
