import "server-only";
import { cookies } from "next/headers";
import { db } from "./db";

/**
 * First-party funnel analytics for demand and price testing. Event names and
 * property keys are allow-listed so health information can never be recorded
 * here by accident. No third-party pixels anywhere on the site.
 */
export const EVENT_NAMES = [
  "assessment_started",
  "assessment_completed",
  "path_suggested",
  "plan_viewed",
  "join_started",
  "account_created",
  "order_review_viewed",
  "order_paid",
  "waitlist_joined",
  "lead_submitted",
  "fake_door_clicked",
  "subscription_cancelled",
  "subscription_paused",
  "video_completed",
] as const;
export type EventName = (typeof EVENT_NAMES)[number];

const ALLOWED_PROPS = new Set(["plan", "variant", "path", "jurisdiction", "source", "kind", "door", "step", "reason", "video", "medical_interest"]);

export async function track(name: EventName, props: Record<string, string | number | boolean | null> = {}, userId?: string | null): Promise<void> {
  const clean: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(props)) if (ALLOWED_PROPS.has(k)) clean[k] = v;
  let anon: string | null = null;
  try {
    anon = (await cookies()).get("rc_anon")?.value ?? null;
  } catch {}
  db("platform").prepare("INSERT INTO events (anon_id, user_id, name, props_json) VALUES (?,?,?,?)").run(anon, userId ?? null, name, JSON.stringify(clean));
}

export function isEventName(x: unknown): x is EventName {
  return typeof x === "string" && (EVENT_NAMES as readonly string[]).includes(x);
}
