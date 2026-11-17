"use client";

import { useActionState, useEffect, useRef, useState } from "react";
import { submitFormCheck } from "@/app/actions/form-checks";
import type { Analysis } from "@/lib/pose-browser";
import { METRICS, type FormExerciseId } from "@/lib/mechanics";

interface Props {
  mode: "member" | "coach";
  memberId?: string;
  memberName?: string;
  exercises: { id: FormExerciseId; name: string; filming: string[] }[];
  defaultExercise?: string;
  needsConsent: boolean;
  consentText: string;
  maxSeconds: number;
  allowanceNote?: string;
  disabled?: boolean;
}

type Stage = "idle" | "camera" | "countdown" | "recording" | "analysing" | "ready";

const pickMime = () =>
  ["video/mp4;codecs=avc1", "video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"].find((m) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(m)) ?? "";

export function FormCapture({ mode, memberId, memberName, exercises, defaultExercise, needsConsent, consentText, maxSeconds, allowanceNote, disabled }: Props) {
  const [state, action, pending] = useActionState(submitFormCheck, null);
  const [exercise, setExercise] = useState<FormExerciseId>((exercises.find((e) => e.id === defaultExercise) ?? exercises[0]).id);
  const [stage, setStage] = useState<Stage>("idle");
  const [progress, setProgress] = useState(0);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [count, setCount] = useState(3);
  const [elapsed, setElapsed] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);
  const liveRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const ex = exercises.find((e) => e.id === exercise)!;
  const stopCamera = () => { streamRef.current?.getTracks().forEach((t) => t.stop()); streamRef.current = null; };
  useEffect(() => () => { stopCamera(); if (timerRef.current) clearInterval(timerRef.current); if (preview) URL.revokeObjectURL(preview); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function runAnalysis(file: File) {
    setAnalysis(null);
    setAnalysisError(null);
    setProgress(0);
    setStage("analysing");
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(file));
    try {
      const { analyseVideo } = await import("@/lib/pose-browser");
      setAnalysis(await analyseVideo(file, exercise, maxSeconds, setProgress));
    } catch (e) {
      setAnalysisError((e as Error).message?.includes("under") ? (e as Error).message : "Automatic measurement isn't available for this video. Your coach will still review it.");
    }
    setStage("ready");
  }

  function takeFile(file: File) {
    if (fileRef.current && fileRef.current.files?.[0] !== file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileRef.current.files = dt.files;
    }
    void runAnalysis(file);
  }

  async function openCamera() {
    setAnalysisError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
      streamRef.current = stream;
      setStage("camera");
      requestAnimationFrame(() => { if (liveRef.current) { liveRef.current.srcObject = stream; void liveRef.current.play(); } });
    } catch {
      setAnalysisError("Camera access was blocked. Allow the camera, or choose a video you've already filmed.");
    }
  }

  function startRecording() {
    setStage("countdown");
    setCount(3);
    let n = 3;
    const cd = setInterval(() => {
      n -= 1;
      setCount(n);
      if (n === 0) {
        clearInterval(cd);
        const mime = pickMime();
        const rec = new MediaRecorder(streamRef.current!, mime ? { mimeType: mime } : undefined);
        const chunks: Blob[] = [];
        rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
        rec.onstop = () => {
          if (timerRef.current) clearInterval(timerRef.current);
          stopCamera();
          const type = rec.mimeType || "video/webm";
          const file = new File([new Blob(chunks, { type })], `form-check.${type.includes("mp4") ? "mp4" : "webm"}`, { type });
          takeFile(file);
        };
        recRef.current = rec;
        rec.start(250);
        setElapsed(0);
        setStage("recording");
        const started = Date.now();
        timerRef.current = setInterval(() => {
          const s = (Date.now() - started) / 1000;
          setElapsed(s);
          if (s >= Math.min(30, maxSeconds)) rec.state === "recording" && rec.stop();
        }, 200);
      }
    }, 800);
  }

  const busy = stage === "analysing" || stage === "countdown" || stage === "recording";
  const metricDefs = METRICS[exercise];

  return (
    <form action={action} className="space-y-5">
      {mode === "coach" && <input type="hidden" name="memberId" value={memberId} />}
      <input type="hidden" name="mechanics" value={analysis ? JSON.stringify(analysis.result) : ""} />

      <div className="grid gap-4 sm:grid-cols-[220px_1fr]">
        <label className="text-sm">
          <span className="field-label">Exercise</span>
          <select name="exercise" className="input" value={exercise} onChange={(e) => { setExercise(e.target.value as FormExerciseId); setAnalysis(null); setStage(fileRef.current?.files?.length ? "ready" : "idle"); }} disabled={busy}>
            {exercises.map((e) => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
        </label>
        <div className="rounded-xl bg-bone/60 p-3 text-sm">
          <p className="font-medium">How to film it</p>
          <ul className="mt-1 list-disc pl-5 text-ink-2">{ex.filming.map((f) => <li key={f}>{f}</li>)}</ul>
        </div>
      </div>

      {(stage === "camera" || stage === "countdown" || stage === "recording") && (
        <div className="relative overflow-hidden rounded-2xl bg-ink">
          <video ref={liveRef} className="aspect-video w-full object-cover" muted playsInline aria-label="Camera preview" />
          {stage === "countdown" && <div className="absolute inset-0 grid place-items-center font-mono text-7xl text-lime" aria-live="assertive">{count || "Go"}</div>}
          {stage === "recording" && <div className="absolute left-3 top-3 chip border-transparent bg-ember text-white" aria-live="polite">● REC {elapsed.toFixed(0)}s</div>}
          <div className="absolute inset-x-0 bottom-0 flex justify-center gap-2 p-3">
            {stage === "camera" && <button type="button" onClick={startRecording} className="btn-lime">Start recording</button>}
            {stage === "recording" && <button type="button" onClick={() => recRef.current?.stop()} className="btn-lime">Stop</button>}
            {stage === "camera" && <button type="button" onClick={() => { stopCamera(); setStage("idle"); }} className="btn-ghost !border-paper/40 !text-paper">Cancel</button>}
          </div>
        </div>
      )}

      <div className={`flex flex-wrap items-center gap-3 ${stage === "camera" || stage === "countdown" || stage === "recording" ? "hidden" : ""}`}>
        <button type="button" onClick={openCamera} className="btn-primary" disabled={busy || disabled}>Record with camera</button>
        <label className={`btn-ghost ${busy || disabled ? "pointer-events-none opacity-50" : ""}`}>
          Choose a video
          <input ref={fileRef} type="file" name="clip" accept="video/mp4,video/quicktime,video/webm" capture="environment" className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void runAnalysis(f); }} disabled={busy || disabled} />
        </label>
        <span className="text-xs text-muted">Up to {maxSeconds} seconds · MP4, MOV or WebM{allowanceNote ? ` · ${allowanceNote}` : ""}</span>
      </div>

      {stage === "analysing" && (
        <div role="status" className="rounded-xl border border-line bg-card p-4 text-sm">
          <p className="font-medium">Measuring your movement on this device…</p>
          <div className="mt-2 h-1.5 rounded-full bg-line"><div className="h-1.5 rounded-full bg-series transition-all" style={{ width: `${progress * 100}%` }} /></div>
          <p className="mt-2 text-xs text-muted">The video isn&apos;t sent anywhere for this step.</p>
        </div>
      )}

      {stage === "ready" && (
        <div className="grid gap-4 rounded-2xl border border-line bg-card p-4 md:grid-cols-[1fr_1fr]">
          <div>
            {analysis?.still ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={analysis.still} alt="The deepest point of your best rep, with the joints the phone measured drawn on" className="max-h-96 w-full rounded-xl object-contain" />
            ) : preview ? (
              <video src={preview} controls muted playsInline preload="metadata" className="max-h-96 w-full rounded-xl bg-ink object-contain" />
            ) : null}
            <p className="mt-2 text-xs text-muted">Check the lines sit on your shoulder, hip, knee and ankle. If they don&apos;t, re-film side-on in better light.</p>
          </div>
          <div className="text-sm">
            <p className="font-semibold">Measured on your device <span className="chip ml-1 border-warn/30 bg-warn-soft text-warn">estimate</span></p>
            {analysis ? (
              <>
                <dl className="mt-3 divide-y divide-line">
                  {metricDefs.map((m) => (
                    <div key={m.key} className="flex justify-between gap-4 py-1.5">
                      <dt className="text-ink-2">{m.label}</dt>
                      <dd className="font-semibold tabular-nums">{analysis.result.metrics[m.key] ?? "—"}{analysis.result.metrics[m.key] != null ? m.unit : ""}</dd>
                    </div>
                  ))}
                </dl>
                {analysis.result.notes.map((n) => <p key={n} className="mt-2 rounded-lg bg-warn-soft/60 p-2 text-xs">{n}</p>)}
              </>
            ) : (
              <p className="mt-2 text-ink-2">{analysisError}</p>
            )}
            <p className="mt-3 text-xs text-muted">An estimate from one camera angle, to track change over time — not a safety guarantee. {mode === "member" ? "Your coach" : "You"} will review the clip.</p>
          </div>
        </div>
      )}

      {stage === "ready" && (
        <div className="space-y-3">
          <label className="block text-sm"><span className="field-label">Note for {mode === "member" ? "your coach" : "the member's record"} (optional)</span>
            <input name="note" className="input" placeholder={mode === "member" ? "e.g. left knee felt tight on rep 3" : "e.g. recorded in session, 12 kg"} maxLength={500} />
          </label>
          {mode === "member" && analysis && (
            <label className="flex items-start gap-3 text-sm"><input type="checkbox" name="metricsOnly" className="mt-1 size-4 accent-ink" />
              <span>Share the measurements only — keep the video on my device. <span className="text-muted">(Your coach can&apos;t rate what they can&apos;t see.)</span></span>
            </label>
          )}
          {mode === "member" && needsConsent && (
            <label className="flex items-start gap-3 rounded-xl border border-line bg-bone/50 p-3 text-sm"><input type="checkbox" name="consent" className="mt-1 size-4 accent-ink" />
              <span>{consentText}</span>
            </label>
          )}
          {state?.error && <p role="alert" className="rounded-lg bg-ember-soft px-3 py-2 text-sm text-ember">{state.error}</p>}
          <button className="btn-primary" disabled={pending}>{pending ? "Saving…" : mode === "member" ? "Save to my programme" : `Save to ${memberName ?? "member"}'s programme`}</button>
        </div>
      )}
      {stage !== "ready" && analysisError && <p role="alert" className="text-sm text-ember">{analysisError}</p>}
    </form>
  );
}
