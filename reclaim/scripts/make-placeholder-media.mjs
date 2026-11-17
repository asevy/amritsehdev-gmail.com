#!/usr/bin/env node
// Generates copyright-free PLACEHOLDER videos, posters, WebVTT captions and chapter
// tracks from content/videos.json using ffmpeg. Replace with produced content later;
// the app only depends on the file layout, not on these renders.
//
//   programme video   -> public/media/public/<id>/{video.mp4,poster.jpg,captions.vtt,chapters.vtt}
//   demo form checks  -> media/demo-form-checks/<name>.mp4  (NOT web-public; streamed via signed links)
//
// Usage: npm run media
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync, readFileSync, mkdtempSync, rmSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const videos = JSON.parse(readFileSync(join(root, "content/videos.json"), "utf8"));

function findFont(pattern, fallback) {
  try {
    const p = execFileSync("fc-match", ["-f", "%{file}", pattern], { encoding: "utf8" }).trim();
    if (p && existsSync(p)) return p;
  } catch {}
  return fallback;
}
const FONT_BOLD = findFont("DejaVu Sans:bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf");
const FONT_REG = findFont("DejaVu Sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf");
const FONT_MONO = findFont("DejaVu Sans Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf");

const ts = (s) => {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = (s % 60).toFixed(3);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${sec.padStart(6, "0")}`;
};

const CATEGORY_LABEL = { programme: "PROGRAMME", movement: "MOVEMENT LIBRARY", lesson: "LESSON", assessment: "ASSESSMENT" };

for (const v of videos) {
  const outDir = join(root, "public/media/public", v.id);
  mkdirSync(outDir, { recursive: true });
  const tmp = mkdtempSync(join(tmpdir(), "reclaim-media-"));
  const tf = (name, text) => { const p = join(tmp, name); writeFileSync(p, text); return p; };

  const filters = [
    // brand + category labels
    `drawtext=fontfile=${FONT_BOLD}:textfile=${tf("brand.txt", "RECLAIM")}:fontcolor=0xD8F26A:fontsize=30:x=80:y=70`,
    `drawtext=fontfile=${FONT_MONO}:textfile=${tf("cat.txt", CATEGORY_LABEL[v.category] ?? "VIDEO")}:fontcolor=0x9FB3AC:fontsize=22:x=80:y=120`,
    `drawtext=fontfile=${FONT_BOLD}:textfile=${tf("title.txt", v.title)}:fontcolor=0xFAF8F3:fontsize=54:x=80:y=250`,
    `drawtext=fontfile=${FONT_MONO}:textfile=${tf("ph.txt", "PLACEHOLDER VIDEO - replace with produced content")}:fontcolor=0x6F837C:fontsize=20:x=80:y=h-80`,
    // running clock
    `drawtext=fontfile=${FONT_MONO}:text='%{pts\\:gmtime\\:0\\:%M\\\\\\:%S}':fontcolor=0x9FB3AC:fontsize=22:x=w-160:y=70`,
    // progress bar
    `drawbox=x=80:y=h-130:w=1120:h=4:color=0x2B3B36:t=fill`,
    `drawbox=x=80:y=h-130:w='max(1,1120*t/${v.durationS})':h=4:color=0xD8F26A:t=fill`,
  ];
  v.chapters.forEach((c, i) => {
    const end = v.chapters[i + 1]?.t ?? v.durationS;
    filters.push(
      `drawtext=fontfile=${FONT_MONO}:textfile=${tf(`chn${i}.txt`, String(i + 1).padStart(2, "0"))}:fontcolor=0xD8F26A:fontsize=26:x=80:y=370:enable='between(t,${c.t},${end})'`,
      `drawtext=fontfile=${FONT_REG}:textfile=${tf(`ch${i}.txt`, c.title)}:fontcolor=0xDDE6E2:fontsize=40:x=130:y=362:enable='between(t,${c.t},${end})'`,
    );
  });

  const mp4 = join(outDir, "video.mp4");
  execFileSync("ffmpeg", [
    "-y", "-loglevel", "error",
    "-f", "lavfi", "-i", `color=c=0x0F1F1B:s=1280x720:d=${v.durationS}:r=24`,
    "-f", "lavfi", "-i", `anullsrc=r=44100:cl=mono`,
    "-vf", filters.join(","),
    "-t", String(v.durationS),
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "32", "-tune", "stillimage", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "32k", "-shortest",
    "-movflags", "+faststart", mp4,
  ]);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-ss", "1", "-i", mp4, "-frames:v", "1", "-q:v", "4", join(outDir, "poster.jpg")]);

  const captions = ["WEBVTT", "", ...v.cues.flatMap((c, i) => [`${i + 1}`, `${ts(c.start)} --> ${ts(c.end)}`, c.text, ""])].join("\n");
  writeFileSync(join(outDir, "captions.vtt"), captions);
  const chapters = ["WEBVTT", "", ...v.chapters.flatMap((c, i) => {
    const end = v.chapters[i + 1]?.t ?? v.durationS;
    return [`ch${i + 1}`, `${ts(c.t)} --> ${ts(end)}`, c.title, ""];
  })].join("\n");
  writeFileSync(join(outDir, "chapters.vtt"), chapters);

  rmSync(tmp, { recursive: true, force: true });
  console.log(`${v.access.padEnd(6)} ${v.id}`);
}

// Demo form-check clips: portrait, like a phone recording. Stand-ins for a member's own video.
const FORM_DEMOS = [
  ["goblet-squat-week1", "Goblet squat", "Week 1 · recorded by coach"],
  ["goblet-squat-week7", "Goblet squat", "Week 7 · recorded by member"],
  ["hip-hinge-week9", "Hip hinge", "Week 9 · recorded by member"],
];
const demoDir = join(root, "media/demo-form-checks");
mkdirSync(demoDir, { recursive: true });
for (const [name, exercise, when] of FORM_DEMOS) {
  const tmp = mkdtempSync(join(tmpdir(), "reclaim-fc-"));
  const tf = (n, text) => { const p = join(tmp, n); writeFileSync(p, text); return p; };
  const vf = [
    `drawtext=fontfile=${FONT_MONO}:textfile=${tf("a.txt", "FORM CHECK")}:fontcolor=0xD8F26A:fontsize=30:x=48:y=96`,
    `drawtext=fontfile=${FONT_BOLD}:textfile=${tf("b.txt", exercise)}:fontcolor=0xFAF8F3:fontsize=56:x=48:y=150`,
    `drawtext=fontfile=${FONT_REG}:textfile=${tf("c.txt", when)}:fontcolor=0x9FB3AC:fontsize=30:x=48:y=230`,
    `drawtext=fontfile=${FONT_MONO}:textfile=${tf("d.txt", "PLACEHOLDER")}:fontcolor=0x6F837C:fontsize=26:x=48:y=h-180`,
    `drawtext=fontfile=${FONT_MONO}:textfile=${tf("e.txt", "A member's own phone video")}:fontcolor=0x6F837C:fontsize=26:x=48:y=h-140`,
    `drawtext=fontfile=${FONT_MONO}:textfile=${tf("f.txt", "appears here.")}:fontcolor=0x6F837C:fontsize=26:x=48:y=h-104`,
    `drawbox=x=48:y=h-240:w='max(1,624*t/6)':h=4:color=0xD8F26A:t=fill`,
  ];
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x0F1F1B:s=720x1280:d=6:r=24", "-vf", vf.join(","), "-t", "6",
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "32", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-movflags", "+faststart", join(demoDir, `${name}.mp4`)]);
  rmSync(tmp, { recursive: true, force: true });
  console.log(`demo   ${name}`);
}
