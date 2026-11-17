import "server-only";
import { mkdirSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { db, newId, nowIso, audit } from "./db";
import { activeSubscription } from "./commerce";
import { hasConsent } from "./consent";
import { signMediaToken } from "./media-auth";
import { planById } from "@/config/catalog";
import { FORM_CHECK_LIMITS, formExerciseById } from "@/config/exercises";
import { parseMechanics, type FormExerciseId, type MechanicsResult } from "./mechanics";
import type { User } from "./auth";

/**
 * Form checks: a member's own exercise clips — recorded by the member or by their coach —
 * plus on-device mechanics estimates and coach ratings. Everything is kept in the member's
 * programme so their technique history builds up over time.
 */
const DATA_DIR = process.env.RECLAIM_DATA_DIR ?? join(process.cwd(), ".data");
const STORE = join(DATA_DIR, "uploads", "form-checks");
const DEMO_DIR = join(process.cwd(), "media", "demo-form-checks");
export const RETEST_DAYS = 28;

export interface FormCheck {
  id: string;
  user_id: string;
  exercise: FormExerciseId;
  file_path: string | null;
  mime: string | null;
  member_note: string | null;
  recorded_by: "member" | "coach";
  recorded_by_id: string;
  mechanics: MechanicsResult | null;
  status: "submitted" | "reviewed" | "deleted";
  created_at: string;
  reviewer_id: string | null;
  reviewed_at: string | null;
  scores: Record<string, number> | null;
  cues: string | null;
}

function hydrate(r: Record<string, unknown>): FormCheck {
  return {
    ...(r as unknown as FormCheck),
    mechanics: r.mechanics_json ? JSON.parse(String(r.mechanics_json)) : null,
    scores: r.scores_json ? JSON.parse(String(r.scores_json)) : null,
  };
}

export function filePathFor(fc: Pick<FormCheck, "file_path">): string | null {
  if (!fc.file_path) return null;
  if (fc.file_path.startsWith("demo:")) return join(DEMO_DIR, fc.file_path.slice(5).replace(/[^a-z0-9.-]/gi, ""));
  return join(STORE, fc.file_path);
}

/** Signed playback URL for a viewer who has already been authorised. */
export function clipUrl(viewerId: string, fc: Pick<FormCheck, "id" | "file_path">): string | null {
  if (!fc.file_path) return null;
  return `/media-secure/form-check/${fc.id}?t=${encodeURIComponent(signMediaToken(viewerId, `fc:${fc.id}`))}`;
}

export function getFormCheck(id: string): FormCheck | null {
  const r = db("platform").prepare("SELECT * FROM form_checks WHERE id = ?").get(id) as Record<string, unknown> | undefined;
  return r ? hydrate(r) : null;
}

/** Only the member and coaches may see a member's clips. Founders/admins, clinicians and pharmacists may not. */
export function canView(viewer: { id: string; role: string }, fc: FormCheck): boolean {
  if (fc.status === "deleted") return false;
  return viewer.id === fc.user_id || viewer.role === "coach";
}

export function listForMember(userId: string): FormCheck[] {
  return (db("platform").prepare("SELECT * FROM form_checks WHERE user_id = ? AND status <> 'deleted' ORDER BY created_at").all(userId) as Record<string, unknown>[]).map(hydrate);
}

export function allowance(userId: string): { limit: number; used: number; plan: string | null } {
  const sub = activeSubscription(userId);
  const plan = sub ? planById(sub.plan_id) : null;
  const monthStart = new Date();
  monthStart.setUTCDate(1);
  monthStart.setUTCHours(0, 0, 0, 0);
  const used = (db("platform").prepare(
    "SELECT COUNT(*) AS n FROM form_checks WHERE user_id = ? AND recorded_by = 'member' AND created_at >= ? AND NOT (status = 'deleted' AND reviewed_at IS NULL)",
  ).get(userId, monthStart.toISOString()) as { n: number }).n;
  return { limit: plan?.formChecksPerMonth ?? 0, used, plan: plan?.name ?? null };
}

function sniff(buf: Buffer): { mime: string; ext: string } | null {
  if (buf.length > 12 && buf.subarray(4, 8).toString("latin1") === "ftyp") {
    const brand = buf.subarray(8, 12).toString("latin1");
    return brand.startsWith("qt") ? { mime: "video/quicktime", ext: "mov" } : { mime: "video/mp4", ext: "mp4" };
  }
  if (buf.length > 4 && buf.readUInt32BE(0) === 0x1a45dfa3) return { mime: "video/webm", ext: "webm" };
  return null;
}

export class FormCheckError extends Error {}

/**
 * Save a form check. `actor` is the member (self-recorded, counts against the plan allowance)
 * or a coach recording on the member's behalf (does not use the member's allowance).
 */
export async function createFormCheck(actor: User, input: {
  memberId: string;
  exercise: string;
  file: File | null;
  metricsOnly: boolean;
  note: string;
  mechanicsJson: string;
}): Promise<string> {
  const ex = formExerciseById(input.exercise);
  if (!ex) throw new FormCheckError("Choose an exercise.");
  const asCoach = actor.role === "coach";
  if (!asCoach && actor.id !== input.memberId) throw new FormCheckError("Forbidden");
  if (!activeSubscription(input.memberId)) throw new FormCheckError("Form checks come with a membership.");
  if (!asCoach) {
    const a = allowance(input.memberId);
    if (a.used >= a.limit) throw new FormCheckError(`You've used this month's ${a.limit} form-check review${a.limit === 1 ? "" : "s"} on ${a.plan}. Your coach can still record one with you in a session.`);
  }
  const mechanics = parseMechanics(input.mechanicsJson, ex.id);
  const id = newId("fc");
  let stored: { path: string; mime: string; size: number } | null = null;

  if (!input.metricsOnly) {
    if (!input.file || input.file.size === 0) throw new FormCheckError("Record or choose a video, or choose to share measurements only.");
    if (!asCoach && !hasConsent(input.memberId, "form_check_video")) throw new FormCheckError("Please agree to the form-check video consent first.");
    if (input.file.size > FORM_CHECK_LIMITS.maxBytes) throw new FormCheckError("That video is over 50 MB. Trim it to 10–20 seconds and try again.");
    const buf = Buffer.from(await input.file.arrayBuffer());
    const kind = sniff(buf);
    if (!kind) throw new FormCheckError("That file isn't a supported video (MP4, MOV or WebM).");
    const dir = join(STORE, input.memberId);
    mkdirSync(dir, { recursive: true });
    const rel = `${input.memberId}/${id}.${kind.ext}`;
    writeFileSync(join(STORE, rel), buf);
    stored = { path: rel, mime: kind.mime, size: buf.length };
  } else if (!mechanics) {
    throw new FormCheckError("No measurements to share — the analysis didn't finish. Upload the video instead.");
  }

  db("platform").prepare(
    `INSERT INTO form_checks (id, user_id, exercise, file_path, mime, size_bytes, member_note, recorded_by, recorded_by_id, mechanics_json, status, created_at)
     VALUES (?,?,?,?,?,?,?,?,?,?, 'submitted', ?)`,
  ).run(id, input.memberId, ex.id, stored?.path ?? null, stored?.mime ?? null, stored?.size ?? null, input.note.slice(0, 500) || null,
    asCoach ? "coach" : "member", actor.id, mechanics ? JSON.stringify(mechanics) : null, nowIso());

  // Saved into the programme: tick this week's matching form-check task.
  db("platform").prepare(
    "UPDATE plan_items SET done_at = COALESCE(done_at, ?) WHERE user_id = ? AND form_exercise = ? AND week_start = (SELECT MAX(week_start) FROM plan_items WHERE user_id = ?)",
  ).run(nowIso(), input.memberId, ex.id, input.memberId);
  audit("platform", { actorId: actor.id, actorRole: actor.role, subjectUser: input.memberId, action: `form_check.created.${asCoach ? "by_coach" : "by_member"}`, resource: id });
  return id;
}

export function reviewFormCheck(coach: User, id: string, scores: Record<string, number>, cues: string) {
  if (coach.role !== "coach") throw new FormCheckError("Forbidden");
  const fc = getFormCheck(id);
  if (!fc || fc.status === "deleted") throw new FormCheckError("Not found");
  const ex = formExerciseById(fc.exercise)!;
  const clean: Record<string, number> = {};
  for (const c of ex.criteria) {
    const v = Math.round(Number(scores[c.id]));
    if (![1, 2, 3].includes(v)) throw new FormCheckError(`Rate "${c.label}".`);
    clean[c.id] = v;
  }
  db("platform").prepare("UPDATE form_checks SET status = 'reviewed', reviewer_id = ?, reviewed_at = ?, scores_json = ?, cues = ? WHERE id = ?")
    .run(coach.id, nowIso(), JSON.stringify(clean), cues.slice(0, 2000), id);
  audit("platform", { actorId: coach.id, actorRole: "coach", subjectUser: fc.user_id, action: "form_check.reviewed", resource: id });
}

/** Members can delete any of their videos at any time; ratings and measurements stay in their record unless they ask otherwise. */
export function deleteFormCheckVideo(user: User, id: string, removeEntirely = false) {
  const fc = getFormCheck(id);
  if (!fc || fc.user_id !== user.id) throw new FormCheckError("Not found");
  const p = filePathFor(fc);
  if (p && !fc.file_path!.startsWith("demo:") && existsSync(p)) rmSync(p);
  if (removeEntirely) db("platform").prepare("UPDATE form_checks SET status = 'deleted', file_path = NULL, mime = NULL WHERE id = ?").run(id);
  else db("platform").prepare("UPDATE form_checks SET file_path = NULL, mime = NULL WHERE id = ?").run(id);
  audit("platform", { actorId: user.id, actorRole: user.role, subjectUser: user.id, action: removeEntirely ? "form_check.deleted" : "form_check.video_deleted", resource: id });
}

export function deleteAllVideos(user: User) {
  for (const fc of listForMember(user.id)) if (fc.file_path) deleteFormCheckVideo(user, fc.id);
}

/** Percentage of available rating points (each criterion 1–3). */
export function formScore(fc: FormCheck): number | null {
  if (!fc.scores) return null;
  const vals = Object.values(fc.scores);
  if (!vals.length) return null;
  return Math.round(((vals.reduce((a, b) => a + b, 0) - vals.length) / (vals.length * 2)) * 100);
}

export function nextDue(checks: FormCheck[], exercise: FormExerciseId): Date | null {
  const last = checks.filter((c) => c.exercise === exercise).at(-1);
  if (!last) return null;
  return new Date(Date.parse(last.created_at) + RETEST_DAYS * 86400_000);
}

export function coachReviewQueue() {
  return (db("platform").prepare(
    `SELECT f.*, u.name AS member_name FROM form_checks f JOIN users u ON u.id = f.user_id WHERE f.status = 'submitted' ORDER BY f.created_at`,
  ).all() as Record<string, unknown>[]).map((r) => ({ ...hydrate(r), member_name: String(r.member_name) }));
}
