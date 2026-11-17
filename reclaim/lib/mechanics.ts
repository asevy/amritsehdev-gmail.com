/**
 * Movement mechanics from pose landmarks — pure functions, no dependencies.
 *
 * Runs in the member's browser on landmarks produced by an on-device pose model
 * (MediaPipe Pose Landmarker), and in unit tests on synthetic landmarks.
 *
 * What it is: an ESTIMATE of joint angles, rep count and tempo from a single
 * side-on phone video, to help a member and their coach track technique over
 * time. What it is not: a guarantee of safe lifting, an injury-risk score or a
 * clinical assessment. A coach reviews every clip; nothing here is used for
 * medical decisions. Accuracy must be validated in the pilot (see
 * docs/WEBSITE_SPEC.md §4) before any member-facing claim is made about it.
 */

export type FormExerciseId = "goblet-squat" | "hip-hinge" | "push-up";

export interface Landmark {
  x: number; // normalised 0..1 across image width
  y: number; // normalised 0..1 down image height
  visibility?: number;
}
export interface Frame {
  t: number; // seconds
  lm: Landmark[] | null; // 33 MediaPipe landmarks, or null when no person was found
}

// MediaPipe Pose landmark indices
const IDX = {
  left: { shoulder: 11, elbow: 13, wrist: 15, hip: 23, knee: 25, ankle: 27 },
  right: { shoulder: 12, elbow: 14, wrist: 16, hip: 24, knee: 26, ankle: 28 },
} as const;
export type Side = keyof typeof IDX;

const deg = (r: number) => (r * 180) / Math.PI;

/** Interior angle at b (degrees), correcting normalised x for the image aspect ratio (width / height). */
export function angleAt(a: Landmark, b: Landmark, c: Landmark, aspect = 1): number {
  const v1x = (a.x - b.x) * aspect, v1y = a.y - b.y;
  const v2x = (c.x - b.x) * aspect, v2y = c.y - b.y;
  const dot = v1x * v2x + v1y * v2y;
  const m = Math.hypot(v1x, v1y) * Math.hypot(v2x, v2y);
  if (m === 0) return NaN;
  return deg(Math.acos(Math.max(-1, Math.min(1, dot / m))));
}

/** Lean of the shoulder→hip line away from vertical (0° = upright). */
export function leanFromVertical(shoulder: Landmark, hip: Landmark, aspect = 1): number {
  return deg(Math.atan2(Math.abs(shoulder.x - hip.x) * aspect, Math.abs(hip.y - shoulder.y)));
}

/** The side of the body facing the camera: the one whose key joints are most visible. */
export function pickSide(frames: Frame[]): Side {
  const score = (s: Side) =>
    frames.reduce((sum, f) => {
      if (!f.lm) return sum;
      const i = IDX[s];
      return sum + [i.shoulder, i.hip, i.knee, i.ankle, i.elbow].reduce((acc, k) => acc + (f.lm![k]?.visibility ?? 0), 0);
    }, 0);
  return score("left") >= score("right") ? "left" : "right";
}

export interface FrameAngles {
  knee: number; hip: number; elbow: number; torsoLean: number; bodyLine: number;
}

export function frameAngles(lm: Landmark[], side: Side, aspect: number, minVisibility = 0.5): FrameAngles | null {
  const i = IDX[side];
  const p = (k: number) => lm[k];
  const needed = [i.shoulder, i.hip, i.knee, i.ankle];
  if (needed.some((k) => !p(k) || (p(k).visibility ?? 1) < minVisibility)) return null;
  return {
    knee: angleAt(p(i.hip), p(i.knee), p(i.ankle), aspect),
    hip: angleAt(p(i.shoulder), p(i.hip), p(i.knee), aspect),
    elbow: p(i.elbow) && p(i.wrist) ? angleAt(p(i.shoulder), p(i.elbow), p(i.wrist), aspect) : NaN,
    torsoLean: leanFromVertical(p(i.shoulder), p(i.hip), aspect),
    bodyLine: angleAt(p(i.shoulder), p(i.hip), p(i.ankle), aspect),
  };
}

/** Centred moving average that skips missing values. */
export function smooth(values: Array<number | null>, window = 5): Array<number | null> {
  const h = Math.floor(window / 2);
  return values.map((v, i) => {
    if (v == null) return null;
    let s = 0, n = 0;
    for (let j = Math.max(0, i - h); j <= Math.min(values.length - 1, i + h); j++) {
      const x = values[j];
      if (x != null && Number.isFinite(x)) { s += x; n++; }
    }
    return n ? s / n : null;
  });
}

export interface Rep { startT: number; bottomT: number; endT: number; bottomIndex: number; bottom: number }

/**
 * Reps from a joint-angle signal that is high at the top of a rep and low at the bottom
 * (knee for squats, hip for hinges, elbow for push-ups). Hysteresis between 30% and 70%
 * of the observed range, so small wobbles don't count as reps.
 */
export function detectReps(t: number[], signal: Array<number | null>, minRangeDeg = 25): Rep[] {
  const vals = signal.filter((v): v is number => v != null && Number.isFinite(v));
  if (vals.length < 5) return [];
  const max = Math.max(...vals), min = Math.min(...vals), range = max - min;
  if (range < minRangeDeg) return [];
  const hi = max - 0.3 * range, lo = min + 0.3 * range;
  const reps: Rep[] = [];
  let state: "top" | "down" | "unknown" = "unknown";
  let startT = 0, bottom = Infinity, bottomIndex = -1, peak = -Infinity;
  signal.forEach((v, i) => {
    if (v == null) return;
    if (v >= hi) {
      if (state === "down" && bottomIndex >= 0) {
        reps.push({ startT, bottomT: t[bottomIndex], endT: t[i], bottomIndex, bottom });
        peak = -Infinity;
      }
      state = "top";
      // A rep starts when the joint leaves the top position: the last moment within 5% of the range of the peak.
      peak = Math.max(peak, v);
      if (v >= peak - 0.05 * range) startT = t[i];
      bottom = Infinity; bottomIndex = -1;
    } else if (state === "top" || state === "down") {
      if (v <= lo) state = "down";
      if (state === "down" && v < bottom) { bottom = v; bottomIndex = i; }
    }
  });
  return reps;
}

export interface MetricDef {
  key: string;
  label: string;
  unit: string;
  /** How to read a change: "lower" or "higher" is better, or "context" (the coach judges). */
  better: "lower" | "higher" | "context";
}

export const METRICS: Record<FormExerciseId, MetricDef[]> = {
  "goblet-squat": [
    { key: "reps", label: "Reps detected", unit: "", better: "context" },
    { key: "deepestKneeDeg", label: "Knee angle at deepest point", unit: "°", better: "context" },
    { key: "torsoLeanAtBottomDeg", label: "Torso lean at the bottom", unit: "°", better: "lower" },
    { key: "descentSec", label: "Average lowering time", unit: "s", better: "context" },
  ],
  "hip-hinge": [
    { key: "reps", label: "Reps detected", unit: "", better: "context" },
    { key: "deepestHipDeg", label: "Hip angle at deepest point", unit: "°", better: "context" },
    { key: "kneeBendAtBottomDeg", label: "Knee bend at the bottom", unit: "°", better: "context" },
    { key: "descentSec", label: "Average lowering time", unit: "s", better: "context" },
  ],
  "push-up": [
    { key: "reps", label: "Reps detected", unit: "", better: "context" },
    { key: "deepestElbowDeg", label: "Elbow angle at deepest point", unit: "°", better: "context" },
    { key: "maxBodyLineBreakDeg", label: "Largest sag or pike of the body line", unit: "°", better: "lower" },
    { key: "descentSec", label: "Average lowering time", unit: "s", better: "context" },
  ],
};

const PRIMARY: Record<FormExerciseId, keyof FrameAngles> = { "goblet-squat": "knee", "hip-hinge": "hip", "push-up": "elbow" };

export interface MechanicsResult {
  source: "camera-pose";
  model: string;
  exercise: FormExerciseId;
  side: Side;
  framesAnalysed: number;
  detectedPct: number;
  quality: "ok" | "low";
  notes: string[];
  metrics: Record<string, number>;
  /** Bottom of the deepest rep, for drawing the skeleton the member can check. */
  deepest: { t: number; index: number } | null;
  /** Downsampled primary angle over time (≤ 120 points) for the coach's view. */
  trace: Array<[number, number]>;
  demo?: boolean;
}

const round1 = (x: number) => Math.round(x * 10) / 10;

export function analyse(exercise: FormExerciseId, frames: Frame[], aspect: number, model = "unknown"): MechanicsResult {
  const side = pickSide(frames);
  const angles = frames.map((f) => (f.lm ? frameAngles(f.lm, side, aspect) : null));
  const detected = angles.filter(Boolean).length;
  const detectedPct = frames.length ? detected / frames.length : 0;
  const key = PRIMARY[exercise];
  const t = frames.map((f) => f.t);
  const primary = smooth(angles.map((a) => (a && Number.isFinite(a[key]) ? a[key] : null)));
  const reps = detectReps(t, primary);
  const notes: string[] = [];
  if (detectedPct < 0.7) notes.push("The whole body wasn't clearly visible side-on in most of the video. Re-film with your full body in frame.");
  if (reps.length === 0) notes.push("No complete reps were detected. Film at least two slow, full reps.");

  const metrics: Record<string, number> = { reps: reps.length };
  const at = (r: Rep) => angles[r.bottomIndex];
  if (reps.length) {
    const deepest = reps.reduce((a, b) => (b.bottom < a.bottom ? b : a));
    metrics.descentSec = round1(reps.reduce((s, r) => s + (r.bottomT - r.startT), 0) / reps.length);
    if (exercise === "goblet-squat") {
      metrics.deepestKneeDeg = Math.round(deepest.bottom);
      metrics.torsoLeanAtBottomDeg = Math.round(Math.max(...reps.map((r) => at(r)?.torsoLean ?? 0)));
    } else if (exercise === "hip-hinge") {
      metrics.deepestHipDeg = Math.round(deepest.bottom);
      metrics.kneeBendAtBottomDeg = Math.round(180 - (at(deepest)?.knee ?? 180));
    } else {
      metrics.deepestElbowDeg = Math.round(deepest.bottom);
      const breaks = angles.filter(Boolean).map((a) => Math.abs(180 - a!.bodyLine));
      metrics.maxBodyLineBreakDeg = Math.round(Math.max(0, ...breaks));
    }
  }
  const deepestRep = reps.length ? reps.reduce((a, b) => (b.bottom < a.bottom ? b : a)) : null;
  const step = Math.max(1, Math.ceil(frames.length / 120));
  const trace: Array<[number, number]> = [];
  primary.forEach((v, i) => { if (i % step === 0 && v != null) trace.push([round1(t[i]), Math.round(v)]); });

  return {
    source: "camera-pose",
    model,
    exercise,
    side,
    framesAnalysed: frames.length,
    detectedPct: Math.round(detectedPct * 100) / 100,
    quality: detectedPct >= 0.7 && reps.length > 0 ? "ok" : "low",
    notes,
    metrics,
    deepest: deepestRep ? { t: deepestRep.bottomT, index: deepestRep.bottomIndex } : null,
    trace,
  };
}

/** Server-side guard for mechanics JSON posted by the browser. */
export function parseMechanics(json: string, exercise: FormExerciseId): MechanicsResult | null {
  if (!json || json.length > 20_000) return null;
  try {
    const m = JSON.parse(json) as MechanicsResult;
    if (m.source !== "camera-pose" || m.exercise !== exercise || typeof m.metrics !== "object") return null;
    const allowed = new Set(METRICS[exercise].map((d) => d.key));
    const metrics: Record<string, number> = {};
    for (const [k, v] of Object.entries(m.metrics)) if (allowed.has(k) && Number.isFinite(v) && Math.abs(v) < 1000) metrics[k] = v;
    return {
      source: "camera-pose",
      model: String(m.model).slice(0, 60),
      exercise,
      side: m.side === "right" ? "right" : "left",
      framesAnalysed: Math.max(0, Math.min(10_000, Number(m.framesAnalysed) || 0)),
      detectedPct: Math.max(0, Math.min(1, Number(m.detectedPct) || 0)),
      quality: m.quality === "ok" ? "ok" : "low",
      notes: (Array.isArray(m.notes) ? m.notes : []).slice(0, 4).map((n) => String(n).slice(0, 200)),
      metrics,
      deepest: null,
      trace: (Array.isArray(m.trace) ? m.trace : []).slice(0, 120).filter((p) => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite)) as Array<[number, number]>,
    };
  } catch {
    return null;
  }
}
