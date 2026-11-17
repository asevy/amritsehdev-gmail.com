"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Playback } from "@/lib/videos";

interface Props {
  videoId: string;
  title: string;
  playback: Playback;
  chapters: { t: number; title: string }[];
  cues: { start: number; end: number; text: string }[];
  /** Saved resume position (seconds). */
  startAt?: number;
  /** Persist progress to the member's account. */
  trackProgress?: boolean;
}

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export function VideoPlayer({ videoId, title, playback, chapters, cues, startAt = 0, trackProgress = false }: Props) {
  const ref = useRef<HTMLVideoElement>(null);
  const lastSent = useRef(0);
  const [time, setTime] = useState(0);
  const [resumed, setResumed] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [rate, setRate] = useState(1);
  const [showTranscript, setShowTranscript] = useState(false);

  // Attach source: native HLS (Safari) → hls.js (others) → MP4 fallback.
  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    let destroy: (() => void) | undefined;
    if (playback.type === "application/x-mpegURL") {
      if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = playback.src;
      } else {
        import("hls.js").then(({ default: Hls }) => {
          if (Hls.isSupported()) {
            const hls = new Hls({ enableWorker: true });
            hls.loadSource(playback.src);
            hls.attachMedia(video);
            hls.on(Hls.Events.ERROR, (_e, data) => {
              if (data.fatal) {
                hls.destroy();
                video.src = playback.mp4Fallback;
              }
            });
            destroy = () => hls.destroy();
          } else {
            video.src = playback.mp4Fallback;
          }
        });
      }
    } else {
      video.src = playback.src;
    }
    return () => destroy?.();
  }, [playback]);

  const send = useCallback(
    (final = false) => {
      const v = ref.current;
      if (!trackProgress || !v || !v.duration) return;
      const body = JSON.stringify({ videoId, position: v.currentTime, duration: v.duration });
      if (final && typeof navigator.sendBeacon === "function") {
        navigator.sendBeacon("/api/video-progress", new Blob([body], { type: "application/json" }));
        return;
      }
      fetch("/api/video-progress", { method: "POST", headers: { "content-type": "application/json" }, body, keepalive: true })
        .then((r) => r.json())
        .then((j: { completed?: boolean }) => j.completed && setCompleted(true))
        .catch(() => {});
    },
    [trackProgress, videoId],
  );

  useEffect(() => {
    const onHide = () => send(true);
    window.addEventListener("pagehide", onHide);
    return () => window.removeEventListener("pagehide", onHide);
  }, [send]);

  const onLoaded = () => {
    const v = ref.current;
    if (!v) return;
    v.textTracks[0] && (v.textTracks[0].mode = "showing");
    if (startAt > 2 && startAt < v.duration - 3 && !resumed) {
      v.currentTime = startAt;
      setResumed(true);
    }
  };

  const onTime = () => {
    const v = ref.current;
    if (!v) return;
    setTime(v.currentTime);
    if (Math.abs(v.currentTime - lastSent.current) >= 10) {
      lastSent.current = v.currentTime;
      send();
    }
  };

  const seek = (t: number) => {
    const v = ref.current;
    if (!v) return;
    v.currentTime = t;
    v.play().catch(() => {});
  };

  const activeChapter = [...chapters].reverse().find((c) => time >= c.t);
  const activeCue = cues.find((c) => time >= c.start && time < c.end);

  return (
    <div>
      <div className="overflow-hidden rounded-2xl border border-line bg-ink">
        <video
          ref={ref}
          className="aspect-video w-full"
          controls
          playsInline
          preload="metadata"
          poster={playback.poster}
          crossOrigin="anonymous"
          aria-label={title}
          onLoadedMetadata={onLoaded}
          onTimeUpdate={onTime}
          onPause={() => send()}
          onEnded={() => send()}
        >
          <track kind="captions" src={playback.captions} srcLang="en" label="English" default />
          <track kind="chapters" src={playback.chapters} srcLang="en" label="Chapters" />
        </video>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
        {resumed && (
          <span className="chip border-moss/30 bg-moss-soft text-moss">
            Resumed at {fmt(startAt)}
            <button className="underline" onClick={() => seek(0)}>
              start over
            </button>
          </span>
        )}
        {completed && <span className="chip border-moss/30 bg-moss-soft text-moss">Completed · saved to your plan</span>}
        <label className="ml-auto flex items-center gap-2 text-xs text-muted">
          Speed
          <select
            className="rounded-lg border border-line-2 bg-card px-2 py-1 text-xs text-ink"
            value={rate}
            onChange={(e) => {
              const r = Number(e.target.value);
              setRate(r);
              if (ref.current) ref.current.playbackRate = r;
            }}
          >
            {[0.75, 1, 1.25, 1.5].map((r) => (
              <option key={r} value={r}>
                {r}×
              </option>
            ))}
          </select>
        </label>
        <button className="btn-ghost btn-sm" aria-expanded={showTranscript} onClick={() => setShowTranscript((s) => !s)}>
          {showTranscript ? "Hide transcript" : "Transcript"}
        </button>
      </div>

      {chapters.length > 1 && (
        <ol className="mt-4 grid gap-2 sm:grid-cols-2" aria-label="Chapters">
          {chapters.map((c, i) => (
            <li key={c.t}>
              <button
                onClick={() => seek(c.t)}
                className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left text-sm transition-colors ${
                  activeChapter?.t === c.t ? "border-ink bg-ink text-paper" : "border-line bg-card hover:bg-bone"
                }`}
              >
                <span className={`font-mono text-xs ${activeChapter?.t === c.t ? "text-lime" : "text-muted"}`}>{String(i + 1).padStart(2, "0")}</span>
                <span className="flex-1">{c.title}</span>
                <span className="font-mono text-xs opacity-70">{fmt(c.t)}</span>
              </button>
            </li>
          ))}
        </ol>
      )}

      {showTranscript && (
        <div className="mt-4 rounded-2xl border border-line bg-card p-4">
          <p className="eyebrow mb-2">Transcript</p>
          <div className="space-y-1">
            {cues.map((c) => (
              <button
                key={c.start}
                onClick={() => seek(c.start)}
                className={`block w-full rounded-lg px-2 py-1.5 text-left text-[15px] leading-6 ${activeCue === c ? "bg-lime/50" : "hover:bg-bone"}`}
              >
                <span className="mr-2 font-mono text-xs text-muted">{fmt(c.start)}</span>
                {c.text}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
