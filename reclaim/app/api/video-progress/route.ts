import { currentUser } from "@/lib/auth";
import { saveProgress } from "@/lib/media-auth";
import { videoById } from "@/lib/videos";
import { track } from "@/lib/analytics";

export async function POST(request: Request) {
  const user = await currentUser();
  if (!user) return Response.json({ error: "unauthorised" }, { status: 401 });
  let body: { videoId?: unknown; position?: unknown; duration?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "bad json" }, { status: 400 });
  }
  const videoId = String(body.videoId ?? "");
  const position = Number(body.position);
  const duration = Number(body.duration);
  if (!videoById(videoId) || !Number.isFinite(position) || !Number.isFinite(duration) || position < 0 || duration <= 0 || position > duration + 1) {
    return Response.json({ error: "invalid" }, { status: 400 });
  }
  const { completed } = saveProgress(user.id, videoId, position, duration);
  if (completed) await track("video_completed", { video: videoId }, user.id);
  return Response.json({ ok: true, completed });
}
