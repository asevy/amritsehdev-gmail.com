import videosJson from "@/content/videos.json";

/**
 * Programme video: ONE public example (the home-page explainer). RECLAIM deliberately does
 * not build a general exercise-video library — that content is abundant elsewhere. The video
 * that is unique to RECLAIM is each member's own form checks (lib/form-checks.ts).
 */
export interface Video {
  id: string;
  title: string;
  summary: string;
  category: string;
  access: "public";
  durationS: number;
  chapters: { t: number; title: string }[];
  cues: { start: number; end: number; text: string }[];
}

export const VIDEOS = videosJson as Video[];
export const videoById = (id: string) => VIDEOS.find((v) => v.id === id);

export interface Playback { src: string; poster: string; captions: string; chapters: string }

export function publicPlayback(v: Video): Playback {
  const base = `/media/public/${v.id}`;
  return { src: `${base}/video.mp4`, poster: `${base}/poster.jpg`, captions: `${base}/captions.vtt`, chapters: `${base}/chapters.vtt` };
}
