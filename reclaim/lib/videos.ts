import videosJson from "@/content/videos.json";

export type VideoCategory = "programme" | "movement" | "lesson" | "assessment";
export interface Video {
  id: string;
  title: string;
  summary: string;
  category: VideoCategory;
  access: "public" | "member";
  durationS: number;
  hls?: boolean;
  chapters: { t: number; title: string }[];
  cues: { start: number; end: number; text: string }[];
}

export const VIDEOS = videosJson as Video[];
export const videoById = (id: string) => VIDEOS.find((v) => v.id === id);

export const CATEGORY_LABEL: Record<VideoCategory, string> = {
  programme: "Programme",
  movement: "Movement library",
  lesson: "Lessons",
  assessment: "Assessments",
};

export interface Playback {
  src: string;
  type: "video/mp4" | "application/x-mpegURL";
  mp4Fallback: string;
  poster: string;
  captions: string;
  chapters: string;
}

/** Public videos are static files under /public. */
export function publicPlayback(v: Video): Playback {
  const base = `/media/public/${v.id}`;
  return {
    src: v.hls ? `${base}/hls/index.m3u8` : `${base}/video.mp4`,
    type: v.hls ? "application/x-mpegURL" : "video/mp4",
    mp4Fallback: `${base}/video.mp4`,
    poster: `${base}/poster.jpg`,
    captions: `${base}/captions.vtt`,
    chapters: `${base}/chapters.vtt`,
  };
}
