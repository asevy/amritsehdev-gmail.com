#!/usr/bin/env node
// Self-hosts the on-device pose model so no third-party origin is contacted from the browser:
//  - copies the MediaPipe WASM runtime from node_modules to public/mediapipe/wasm
//  - downloads pose_landmarker_lite.task (Apache-2.0) to public/models once
// Both folders are gitignored. If the download fails, form checks still work; automatic
// measurement is skipped and the member is told so.
import { cpSync, existsSync, mkdirSync, writeFileSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "node_modules/@mediapipe/tasks-vision/wasm");
const wasmDir = join(root, "public/mediapipe/wasm");
const modelPath = join(root, "public/models/pose_landmarker_lite.task");
const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

if (existsSync(src)) {
  mkdirSync(wasmDir, { recursive: true });
  cpSync(src, wasmDir, { recursive: true });
} else {
  console.warn("setup-pose: @mediapipe/tasks-vision not installed — run npm install");
}

if (existsSync(modelPath) && statSync(modelPath).size > 1_000_000) process.exit(0);
try {
  const res = await fetch(MODEL_URL, { signal: AbortSignal.timeout(60_000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  mkdirSync(dirname(modelPath), { recursive: true });
  writeFileSync(modelPath, Buffer.from(await res.arrayBuffer()));
  console.log(`setup-pose: model saved (${(statSync(modelPath).size / 1e6).toFixed(1)} MB)`);
} catch (e) {
  console.warn(`setup-pose: could not download the pose model (${e.message}). Form checks work without it; automatic measurement is skipped.`);
}
