import "server-only";
import { db } from "./db";
import { listForMember, formScore } from "./form-checks";
import { METRIC_META } from "./portal-data";
import { formExerciseById } from "@/config/exercises";
import { planById } from "@/config/catalog";
import { fmtDate } from "./money";

/**
 * The member's record: everything they've done in the programme, newest first. It only
 * ever grows, so the longer someone stays the more it's worth to them. It is fully
 * exportable (Privacy & data); value, not lock-in, is what keeps people.
 * Medical-practice records are not included — they belong to the practice (see Care).
 */
export type RecordKind = "milestone" | "form" | "measure" | "blueprint" | "session" | "week" | "membership";
export interface RecordEvent { at: string; kind: RecordKind; title: string; detail?: string; href?: string }

export function memberRecord(userId: string) {
  const d = db("platform");
  const events: RecordEvent[] = [];

  const subs = d.prepare("SELECT plan_id, started_at FROM subscriptions WHERE user_id = ? ORDER BY started_at").all(userId) as Array<{ plan_id: string; started_at: string }>;
  subs.forEach((s) => events.push({ at: s.started_at, kind: "membership", title: `Joined ${planById(s.plan_id)?.name ?? s.plan_id}` }));

  (d.prepare("SELECT version, author, created_at FROM blueprints WHERE user_id = ? ORDER BY version").all(userId) as Array<{ version: number; author: string; created_at: string }>)
    .forEach((b) => events.push({ at: b.created_at, kind: "blueprint", title: `Blueprint v${b.version}`, detail: b.author, href: "/portal/blueprint" }));

  // Measurements grouped by day, and personal bests as milestones.
  const ms = d.prepare("SELECT metric, value, unit, measured_at FROM measurements WHERE user_id = ? ORDER BY measured_at").all(userId) as Array<{ metric: string; value: number; unit: string; measured_at: string }>;
  const byDay = new Map<string, typeof ms>();
  const best = new Map<string, number>();
  let personalBests = 0;
  for (const m of ms) {
    const day = m.measured_at.slice(0, 10);
    byDay.set(day, [...(byDay.get(day) ?? []), m]);
    const meta = METRIC_META[m.metric];
    if (!meta) continue;
    const prev = best.get(m.metric);
    const better = prev == null ? false : meta.better === "up" ? m.value > prev : m.value < prev;
    if (prev == null || better) best.set(m.metric, m.value);
    if (better && ["sit_to_stand", "waist_cm", "steps", "lean_mass_kg"].includes(m.metric)) {
      personalBests++;
      events.push({ at: m.measured_at, kind: "milestone", title: `Personal best: ${meta.label.toLowerCase()}`, detail: `${m.value.toLocaleString("en-CA")} ${meta.unit} (was ${prev!.toLocaleString("en-CA")})`, href: "/portal/progress" });
    }
  }
  for (const [day, list] of byDay) {
    events.push({
      at: list[0].measured_at, kind: "measure", title: `Logged ${list.length === 1 ? (METRIC_META[list[0].metric]?.label.toLowerCase() ?? list[0].metric) : `${list.length} measurements`}`,
      detail: list.map((m) => `${METRIC_META[m.metric]?.label ?? m.metric} ${m.value.toLocaleString("en-CA")} ${METRIC_META[m.metric]?.unit ?? m.unit}`).join(" · "), href: "/portal/progress",
    });
    void day;
  }

  // Form checks, and a milestone when a form score improves.
  const checks = listForMember(userId);
  const lastScore = new Map<string, number>();
  for (const c of checks) {
    const ex = formExerciseById(c.exercise);
    events.push({ at: c.created_at, kind: "form", title: `${ex?.name ?? c.exercise} form check`, detail: c.recorded_by === "coach" ? "Recorded by your coach" : c.member_note ?? "Recorded by you", href: `/portal/form-checks#${c.exercise}` });
    if (c.reviewed_at) {
      const s = formScore(c);
      events.push({ at: c.reviewed_at, kind: "form", title: `Coach reviewed your ${ex?.name.toLowerCase() ?? c.exercise}`, detail: `${s != null ? `Form score ${s}%. ` : ""}${c.cues ?? ""}`, href: `/portal/form-checks#${c.exercise}` });
      const prev = lastScore.get(c.exercise);
      if (s != null && prev != null && s > prev) {
        events.push({ at: c.reviewed_at, kind: "milestone", title: `Form improved: ${ex?.name.toLowerCase()}`, detail: `Form score ${prev}% → ${s}%`, href: `/portal/form-checks#${c.exercise}` });
      }
      if (s != null) lastScore.set(c.exercise, s);
    }
  }

  (d.prepare("SELECT title, starts_at, kind FROM bookings WHERE user_id = ? AND status = 'completed' ORDER BY starts_at").all(userId) as Array<{ title: string; starts_at: string; kind: string }>)
    .forEach((b) => events.push({ at: b.starts_at, kind: "session", title: b.title, detail: b.kind === "partner" ? "Partner session" : "With your coach" }));

  (d.prepare("SELECT week_start, COUNT(*) AS total, SUM(done_at IS NOT NULL) AS done FROM plan_items WHERE user_id = ? GROUP BY week_start ORDER BY week_start").all(userId) as Array<{ week_start: string; total: number; done: number }>)
    .forEach((w) => events.push({ at: `${w.week_start}T12:00:00.000Z`, kind: "week", title: `Week of ${fmtDate(`${w.week_start}T12:00:00.000Z`, { month: "short", day: "numeric" })}`, detail: `${w.done} of ${w.total} plan items done`, href: "/portal/plan" }));

  events.sort((a, b) => b.at.localeCompare(a.at));
  const since = subs[0]?.started_at ?? null;
  return {
    events,
    summary: {
      since,
      weeks: since ? Math.max(1, Math.round((Date.now() - Date.parse(since)) / (7 * 86400_000))) : 0,
      formChecks: checks.length,
      measurements: ms.length,
      personalBests,
      sessions: events.filter((e) => e.kind === "session").length,
    },
  };
}
