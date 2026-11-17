/**
 * Browser-only: on-device pose estimation for form checks (MediaPipe Pose Landmarker, Apache-2.0).
 * The model and WASM runtime are self-hosted under /models and /mediapipe (scripts/setup-pose.mjs);
 * video frames never leave the device for analysis — only the resulting numbers are sent.
 */
import type { PoseLandmarker, NormalizedLandmark } from "@mediapipe/tasks-vision";
import { analyse, type Frame, type FormExerciseId, type Landmark, type MechanicsResult } from "./mechanics";

export const POSE_MODEL = "mediapipe-pose-landmarker-lite";
const FPS = 10;

let landmarker: Promise<PoseLandmarker> | null = null;
let lastTs = 0;

/** MediaPipe's WASM runtime writes routine status lines ("INFO: …", glog "I0000/W0000 …") to console.error. */
function quietMediapipeLogs() {
  const g = globalThis as unknown as { __rcQuiet?: boolean };
  if (g.__rcQuiet) return;
  g.__rcQuiet = true;
  const orig = console.error.bind(console);
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === "string" && /^(INFO:|[IW]\d{4} )/.test(args[0])) return;
    orig(...args);
  };
}

export function loadLandmarker(): Promise<PoseLandmarker> {
  quietMediapipeLogs();
  landmarker ??= (async () => {
    const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");
    const fileset = await FilesetResolver.forVisionTasks("/mediapipe/wasm");
    return PoseLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: "/models/pose_landmarker_lite.task", delegate: "CPU" },
      runningMode: "VIDEO",
      numPoses: 1,
    });
  })();
  landmarker.catch(() => (landmarker = null));
  return landmarker;
}

const once = (el: HTMLElement, ev: string) => new Promise<void>((res, rej) => {
  const ok = () => { cleanup(); res(); };
  const bad = () => { cleanup(); rej(new Error("This video can't be read in the browser.")); };
  const cleanup = () => { el.removeEventListener(ev, ok); el.removeEventListener("error", bad); };
  el.addEventListener(ev, ok, { once: true });
  el.addEventListener("error", bad, { once: true });
});

async function seek(video: HTMLVideoElement, t: number) {
  const p = once(video, "seeked");
  video.currentTime = t;
  await p;
}

export interface Analysis { result: MechanicsResult; still: string | null; duration: number }

export async function analyseVideo(file: Blob, exercise: FormExerciseId, maxSeconds: number, onProgress: (p: number) => void): Promise<Analysis> {
  const url = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.preload = "auto";
  try {
    const meta = once(video, "loadedmetadata");
    video.src = url;
    await meta;
    // Recordings from MediaRecorder can report an unknown duration until the end has been seeked.
    if (!Number.isFinite(video.duration)) { await seek(video, 1e6); await seek(video, 0); }
    const duration = video.duration;
    if (!Number.isFinite(duration) || duration <= 0) throw new Error("This video has no readable length.");
    if (duration > maxSeconds + 0.5) throw new Error(`Keep form-check videos under ${maxSeconds} seconds.`);

    const lm = await loadLandmarker();
    const frames: Frame[] = [];
    for (let t = 0; t < duration; t += 1 / FPS) {
      await seek(video, t);
      lastTs = Math.max(lastTs + 1, Math.round(performance.now()));
      const r = lm.detectForVideo(video, lastTs);
      frames.push({ t, lm: (r.landmarks?.[0] as NormalizedLandmark[] | undefined) ?? null });
      onProgress(Math.min(1, t / duration));
    }
    const aspect = video.videoWidth / video.videoHeight || 1;
    const result = analyse(exercise, frames, aspect, POSE_MODEL);
    let still: string | null = null;
    if (result.deepest) {
      await seek(video, result.deepest.t);
      still = drawSkeleton(video, frames[result.deepest.index].lm!, result);
    }
    onProgress(1);
    return { result, still, duration };
  } finally {
    URL.revokeObjectURL(url);
  }
}

const SIDE = { left: [11, 13, 15, 23, 25, 27], right: [12, 14, 16, 24, 26, 28] } as const;

/** Frame at the deepest point with the detected joints drawn on, so the member can see what was measured. */
function drawSkeleton(video: HTMLVideoElement, lm: Landmark[], r: MechanicsResult): string {
  const w = 480, h = Math.round((480 * video.videoHeight) / video.videoWidth) || 270;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const g = c.getContext("2d")!;
  g.drawImage(video, 0, 0, w, h);
  const [sh, el, wr, hip, kn, an] = SIDE[r.side].map((i) => ({ x: lm[i].x * w, y: lm[i].y * h }));
  g.strokeStyle = "#d8f26a";
  g.lineWidth = 4;
  g.lineCap = "round";
  for (const [a, b] of [[sh, hip], [hip, kn], [kn, an], [sh, el], [el, wr]] as const) {
    g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke();
  }
  g.fillStyle = "#0f1f1b";
  for (const p of [sh, el, wr, hip, kn, an]) { g.beginPath(); g.arc(p.x, p.y, 5, 0, Math.PI * 2); g.fill(); }
  const label = r.exercise === "goblet-squat" ? `Knee ${r.metrics.deepestKneeDeg}°` : r.exercise === "hip-hinge" ? `Hip ${r.metrics.deepestHipDeg}°` : `Elbow ${r.metrics.deepestElbowDeg}°`;
  const at = r.exercise === "goblet-squat" ? kn : r.exercise === "hip-hinge" ? hip : el;
  g.font = "600 15px system-ui, sans-serif";
  const tw = g.measureText(label).width;
  g.fillStyle = "rgba(15,31,27,0.85)";
  g.fillRect(at.x + 10, at.y - 22, tw + 14, 24);
  g.fillStyle = "#faf8f3";
  g.fillText(label, at.x + 17, at.y - 5);
  return c.toDataURL("image/jpeg", 0.85);
}
