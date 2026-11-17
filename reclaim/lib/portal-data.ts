import "server-only";
import { db } from "./db";

export interface PlanItem { id: number; week_start: string; day: number; kind: string; title: string; detail: string | null; video_id: string | null; done_at: string | null }
export interface Booking { id: string; kind: string; partner_id: string | null; title: string; starts_at: string; duration_min: number; status: string; credits_used: number }
export interface Measurement { metric: string; value: number; unit: string; source: string; measured_at: string; note: string | null }

export function currentWeekItems(userId: string): PlanItem[] {
  return db("platform").prepare(
    "SELECT * FROM plan_items WHERE user_id = ? AND week_start = (SELECT MAX(week_start) FROM plan_items WHERE user_id = ?) ORDER BY day, id",
  ).all(userId, userId) as unknown as PlanItem[];
}

export function bookings(userId: string): Booking[] {
  return db("platform").prepare("SELECT * FROM bookings WHERE user_id = ? ORDER BY starts_at").all(userId) as unknown as Booking[];
}

export function measurements(userId: string): Measurement[] {
  return db("platform").prepare("SELECT metric, value, unit, source, measured_at, note FROM measurements WHERE user_id = ? ORDER BY measured_at").all(userId) as unknown as Measurement[];
}

export function latestBlueprint(userId: string) {
  return (db("platform").prepare("SELECT * FROM blueprints WHERE user_id = ? ORDER BY version DESC LIMIT 1").get(userId) as
    | { version: number; data_json: string; source: string; author: string; created_at: string }
    | undefined) ?? null;
}

export function blueprintVersions(userId: string) {
  return db("platform").prepare("SELECT version, source, author, created_at FROM blueprints WHERE user_id = ? ORDER BY version DESC").all(userId) as Array<{ version: number; source: string; author: string; created_at: string }>;
}

export function coachMessages(userId: string) {
  return db("platform").prepare("SELECT * FROM messages WHERE user_id = ? ORDER BY id").all(userId) as Array<{ id: number; sender_role: string; sender_name: string; body: string; created_at: string }>;
}

export function creditHistory(userId: string) {
  return db("platform").prepare("SELECT delta, reason, expires_at, created_at FROM credits_ledger WHERE user_id = ? ORDER BY id DESC").all(userId) as Array<{ delta: number; reason: string; expires_at: string | null; created_at: string }>;
}

export function orders(userId: string) {
  return db("platform").prepare("SELECT id, status, total_cents, tax_cents, created_at, paid_at, agreement_sha FROM orders WHERE user_id = ? ORDER BY created_at DESC").all(userId) as Array<{
    id: string; status: string; total_cents: number; tax_cents: number; created_at: string; paid_at: string | null; agreement_sha: string;
  }>;
}

export const METRIC_META: Record<string, { label: string; unit: string; decimals: number; better: "up" | "down" }> = {
  weight_kg: { label: "Body weight", unit: "kg", decimals: 1, better: "down" },
  waist_cm: { label: "Waist circumference", unit: "cm", decimals: 1, better: "down" },
  sit_to_stand: { label: "30-second sit-to-stand", unit: "reps", decimals: 0, better: "up" },
  steps: { label: "Average daily steps", unit: "steps", decimals: 0, better: "up" },
  sleep_h: { label: "Average sleep", unit: "h", decimals: 1, better: "up" },
  lean_mass_kg: { label: "Lean mass (partner scan)", unit: "kg", decimals: 1, better: "up" },
  body_fat_pct: { label: "Body fat (partner scan)", unit: "%", decimals: 1, better: "down" },
};

export const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
