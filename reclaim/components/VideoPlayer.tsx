"use client";

import { useRef, useState } from "react";
import type { Playback } from "@/lib/videos";

/** Accessible player for the programme explainer: captions on by default, chapters, clickable transcript. */
export function VideoPlayer({ title, playback, chapters, cues }: {
  title: string;
  playback: Playback;
  chapters: { t: number; title: string }[];
  cues: { start: number; end: number; text: string }[];
}) {
  const ref = useRef<HTMLVideoElement>(null);
  const [time, setTime] = useState(0);
  const [showTranscript, setShowTranscript] = useState(false);
  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const seek = (t: number) => {
    if (!ref.current) return;
    ref.current.currentTime = t;
    void ref.current.play().catch(() => {});
  };
  const activeChapter = [...chapters].reverse().find((c) => time >= c.t);
  const activeCue = cues.find((c) => time >= c.start && time < c.end);

  return (
    <div>
      <div className="overflow-hidden rounded-2xl border border-line bg-ink">
        <video
          ref={ref}
          src={playback.src}
          className="aspect-video w-full"
          controls
          playsInline
          preload="metadata"
          poster={playback.poster}
          aria-label={title}
          onLoadedMetadata={() => { const tr = ref.current?.textTracks[0]; if (tr) tr.mode = "showing"; }}
          onTimeUpdate={() => setTime(ref.current?.currentTime ?? 0)}
        >
          <track kind="captions" src={playback.captions} srcLang="en" label="English" default />
          <track kind="chapters" src={playback.chapters} srcLang="en" label="Chapters" />
        </video>
      </div>
      <div className="mt-3 flex justify-end">
        <button className="btn-ghost btn-sm" aria-expanded={showTranscript} onClick={() => setShowTranscript((s) => !s)}>{showTranscript ? "Hide transcript" : "Transcript"}</button>
      </div>
      {chapters.length > 1 && (
        <ol className="mt-3 grid gap-2 sm:grid-cols-2" aria-label="Chapters">
          {chapters.map((c, i) => (
            <li key={c.t}>
              <button onClick={() => seek(c.t)} className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left text-sm transition-colors ${activeChapter?.t === c.t ? "border-ink bg-ink text-paper" : "border-line bg-card hover:bg-bone"}`}>
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
          {cues.map((c) => (
            <button key={c.start} onClick={() => seek(c.start)} className={`block w-full rounded-lg px-2 py-1.5 text-left text-[15px] leading-6 ${activeCue === c ? "bg-lime/50" : "hover:bg-bone"}`}>
              <span className="mr-2 font-mono text-xs text-muted">{fmt(c.start)}</span>{c.text}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
