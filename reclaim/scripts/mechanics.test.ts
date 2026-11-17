// Unit tests for lib/mechanics.ts on synthetic side-view landmarks.
// Run: npm run test:mechanics   (Node 22.18+ strips TypeScript types natively)
import { test } from "node:test";
import assert from "node:assert/strict";
import { angleAt, analyse, detectReps, pickSide, parseMechanics, type Frame, type Landmark } from "../lib/mechanics.ts";

const rad = (d: number) => (d * Math.PI) / 180;

/** Side-view figure (left side facing camera) with a given knee angle and torso lean, aspect 1. */
function squatPose(kneeDeg: number, leanDeg: number, vis = 0.95): Landmark[] {
  const lm: Landmark[] = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, visibility: 0.1 }));
  const ankle = { x: 0.5, y: 0.9 };
  const shinTilt = (180 - kneeDeg) / 2; // shin leans forward by half the knee flexion
  const knee = { x: ankle.x + 0.22 * Math.sin(rad(shinTilt)), y: ankle.y - 0.22 * Math.cos(rad(shinTilt)) };
  // thigh direction: rotate knee→ankle vector so the interior angle at the knee is kneeDeg
  const ka = Math.atan2(ankle.y - knee.y, ankle.x - knee.x);
  const th = ka + rad(kneeDeg);
  const hip = { x: knee.x + 0.22 * Math.cos(th), y: knee.y + 0.22 * Math.sin(th) };
  const shoulder = { x: hip.x + 0.28 * Math.sin(rad(leanDeg)), y: hip.y - 0.28 * Math.cos(rad(leanDeg)) };
  const elbow = { x: shoulder.x + 0.1, y: shoulder.y + 0.12 };
  const wrist = { x: shoulder.x + 0.12, y: shoulder.y };
  Object.entries({ 11: shoulder, 13: elbow, 15: wrist, 23: hip, 25: knee, 27: ankle }).forEach(([i, p]) => (lm[Number(i)] = { ...p, visibility: vis }));
  return lm;
}

function squatVideo(reps: number, deepestKnee: number, fps = 15, secPerRep = 3): Frame[] {
  const frames: Frame[] = [];
  const n = reps * secPerRep * fps + fps; // a second standing at the end
  for (let i = 0; i < n; i++) {
    const t = i / fps;
    const phase = Math.min(1, t / (reps * secPerRep));
    const cyc = phase >= 1 ? 0 : (1 - Math.cos(2 * Math.PI * reps * phase)) / 2; // 0 top → 1 bottom → 0
    const knee = 172 - cyc * (172 - deepestKnee);
    frames.push({ t, lm: squatPose(knee, 10 + cyc * 25) });
  }
  return frames;
}

test("angleAt measures a right angle and a straight line", () => {
  assert.equal(Math.round(angleAt({ x: 0, y: 0 }, { x: 0, y: 1 }, { x: 1, y: 1 })), 90);
  assert.equal(Math.round(angleAt({ x: 0, y: 0 }, { x: 0, y: 1 }, { x: 0, y: 2 })), 180);
});

test("angleAt corrects for image aspect ratio", () => {
  // In a 2:1 frame, 0.25 normalised width equals 0.5 normalised height → 45°, not ~63°.
  const a = angleAt({ x: 0.25, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 0.5 }, 2);
  assert.equal(Math.round(a), 90);
  const lean = Math.atan2(0.25 * 2, 0.5) * (180 / Math.PI);
  assert.equal(Math.round(lean), 45);
});

test("synthetic pose produces the requested knee angle", () => {
  for (const k of [170, 120, 90]) {
    const lm = squatPose(k, 15);
    assert.ok(Math.abs(angleAt(lm[23], lm[25], lm[27]) - k) < 0.5, `knee ${k}`);
  }
});

test("pickSide chooses the more visible side", () => {
  const frames = squatVideo(1, 100);
  assert.equal(pickSide(frames), "left");
});

test("detectReps ignores small wobbles", () => {
  const t = Array.from({ length: 60 }, (_, i) => i / 15);
  const wobble = t.map((x) => 170 + 5 * Math.sin(x * 6));
  assert.equal(detectReps(t, wobble).length, 0);
});

test("analyse counts three squat reps and finds depth and lean", () => {
  const r = analyse("goblet-squat", squatVideo(3, 92), 1, "test");
  assert.equal(r.metrics.reps, 3);
  assert.ok(Math.abs(r.metrics.deepestKneeDeg - 92) <= 4, `deepest ${r.metrics.deepestKneeDeg}`);
  assert.ok(Math.abs(r.metrics.torsoLeanAtBottomDeg - 35) <= 4, `lean ${r.metrics.torsoLeanAtBottomDeg}`);
  assert.ok(r.metrics.descentSec > 1 && r.metrics.descentSec < 2, `descent ${r.metrics.descentSec}`);
  assert.equal(r.quality, "ok");
  assert.ok(r.trace.length > 10 && r.trace.length <= 120);
});

test("a deeper squat reads as a smaller knee angle", () => {
  const shallow = analyse("goblet-squat", squatVideo(2, 125), 1);
  const deep = analyse("goblet-squat", squatVideo(2, 95), 1);
  assert.ok(deep.metrics.deepestKneeDeg < shallow.metrics.deepestKneeDeg);
});

test("frames without a person are reported as low quality, not guessed", () => {
  const frames: Frame[] = Array.from({ length: 45 }, (_, i) => ({ t: i / 15, lm: null }));
  const r = analyse("goblet-squat", frames, 1);
  assert.equal(r.quality, "low");
  assert.equal(r.metrics.reps, 0);
  assert.ok(r.notes.length >= 1);
});

test("parseMechanics drops unknown metrics and rejects the wrong exercise", () => {
  const r = analyse("goblet-squat", squatVideo(2, 100), 1, "test");
  const tampered = JSON.stringify({ ...r, metrics: { ...r.metrics, injected: 5, deepestKneeDeg: 1e9 } });
  const p = parseMechanics(tampered, "goblet-squat")!;
  assert.equal(p.metrics.injected, undefined);
  assert.equal(p.metrics.deepestKneeDeg, undefined);
  assert.equal(parseMechanics(JSON.stringify(r), "push-up"), null);
});
