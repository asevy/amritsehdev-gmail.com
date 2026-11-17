import "server-only";
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { db, nowIso } from "./db";
import type { Video, Playback } from "./videos";
import { activeSubscription } from "./commerce";

/**
 * Members-only media is never placed under /public. Pages mint short-lived HMAC
 * tokens bound to (user, video, expiry); the /media-secure route verifies them and
 * streams with HTTP Range support. This mirrors signed playback URLs from a video
 * host such as Mux or Cloudflare Stream, so swapping hosts changes only this file.
 */
const g = globalThis as unknown as { __mediaSecret?: string };
const SECRET = process.env.RECLAIM_MEDIA_SECRET ?? (g.__mediaSecret ??= randomBytes(32).toString("hex"));
const TTL_S = 60 * 60;

export function signMediaToken(userId: string, videoId: string): string {
  const exp = Math.floor(Date.now() / 1000) + TTL_S;
  const payload = `${userId}.${videoId}.${exp}`;
  const sig = createHmac("sha256", SECRET).update(payload).digest("base64url");
  return `${Buffer.from(payload).toString("base64url")}.${sig}`;
}

export function verifyMediaToken(token: string, videoId: string): { userId: string } | null {
  const [p, sig] = token.split(".");
  if (!p || !sig) return null;
  const payload = Buffer.from(p, "base64url").toString();
  const expected = createHmac("sha256", SECRET).update(payload).digest();
  const given = Buffer.from(sig, "base64url");
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) return null;
  const [userId, vid, exp] = payload.split(".");
  if (vid !== videoId || Number(exp) < Date.now() / 1000) return null;
  return { userId };
}

/** Members with an active or paused membership can stream the member library. */
export function canStreamMemberVideos(userId: string, role: string): boolean {
  if (role !== "member") return role === "coach" || role === "admin";
  return !!activeSubscription(userId);
}

export function memberPlayback(v: Video, userId: string): Playback {
  const t = encodeURIComponent(signMediaToken(userId, v.id));
  const base = `/media-secure/${v.id}`;
  return {
    src: `${base}/video.mp4?t=${t}`,
    type: "video/mp4",
    mp4Fallback: `${base}/video.mp4?t=${t}`,
    poster: `${base}/poster.jpg?t=${t}`,
    captions: `${base}/captions.vtt?t=${t}`,
    chapters: `${base}/chapters.vtt?t=${t}`,
  };
}

export interface ProgressRow {
  video_id: string;
  position_s: number;
  duration_s: number;
  completed_at: string | null;
  saved: number;
  updated_at: string;
}

export function progressFor(userId: string): Map<string, ProgressRow> {
  const rows = db("platform").prepare("SELECT * FROM video_progress WHERE user_id = ?").all(userId) as unknown as ProgressRow[];
  return new Map(rows.map((r) => [r.video_id, r]));
}

export function saveProgress(userId: string, videoId: string, position: number, duration: number): { completed: boolean } {
  const d = db("platform");
  const completed = duration > 0 && position / duration >= 0.9;
  d.prepare(
    `INSERT INTO video_progress (user_id, video_id, position_s, duration_s, completed_at, updated_at) VALUES (?,?,?,?,?,?)
     ON CONFLICT(user_id, video_id) DO UPDATE SET position_s = excluded.position_s, duration_s = excluded.duration_s,
       completed_at = COALESCE(video_progress.completed_at, excluded.completed_at), updated_at = excluded.updated_at`,
  ).run(userId, videoId, position, duration, completed ? nowIso() : null, nowIso());
  if (completed) {
    // Completing a video ticks off the matching item in this week's plan.
    d.prepare("UPDATE plan_items SET done_at = COALESCE(done_at, ?) WHERE user_id = ? AND video_id = ? AND kind IN ('lesson','test','training') AND week_start = (SELECT MAX(week_start) FROM plan_items WHERE user_id = ?)")
      .run(nowIso(), userId, videoId, userId);
  }
  return { completed };
}

export function toggleSaved(userId: string, videoId: string): void {
  db("platform").prepare(
    `INSERT INTO video_progress (user_id, video_id, saved, updated_at) VALUES (?,?,1,?)
     ON CONFLICT(user_id, video_id) DO UPDATE SET saved = 1 - video_progress.saved, updated_at = excluded.updated_at`,
  ).run(userId, videoId, nowIso());
}
