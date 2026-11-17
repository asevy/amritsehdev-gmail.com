import { createReadStream, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import { Readable } from "node:stream";
import { verifyMediaToken, canStreamMemberVideos } from "@/lib/media-auth";
import { videoById } from "@/lib/videos";
import { db } from "@/lib/db";

/**
 * Streams members-only media after verifying a short-lived signed token and the
 * viewer's current entitlement. Supports HTTP Range requests for seeking.
 */
const TYPES: Record<string, string> = {
  "video.mp4": "video/mp4",
  "poster.jpg": "image/jpeg",
  "captions.vtt": "text/vtt",
  "chapters.vtt": "text/vtt",
};

export async function GET(request: Request, ctx: { params: Promise<{ id: string; file: string }> }) {
  const { id, file } = await ctx.params;
  const type = TYPES[file];
  const video = videoById(id);
  if (!type || !video || video.access !== "member") return new Response("Not found", { status: 404 });

  const token = new URL(request.url).searchParams.get("t") ?? "";
  const claims = verifyMediaToken(token, id);
  if (!claims) return new Response("Link expired — reload the page", { status: 403 });
  const user = db("platform").prepare("SELECT role FROM users WHERE id = ?").get(claims.userId) as { role: string } | undefined;
  if (!user || !canStreamMemberVideos(claims.userId, user.role)) return new Response("Membership required", { status: 403 });

  const path = join(process.cwd(), "media/members", id, file);
  if (!existsSync(path)) return new Response("Not found", { status: 404 });
  const size = statSync(path).size;
  const headers = { "Content-Type": type, "Accept-Ranges": "bytes", "Cache-Control": "private, max-age=300" };

  const range = request.headers.get("range");
  if (range && type === "video/mp4") {
    const m = /bytes=(\d*)-(\d*)/.exec(range);
    const start = m?.[1] ? Number(m[1]) : 0;
    const end = m?.[2] ? Math.min(Number(m[2]), size - 1) : size - 1;
    if (start >= size || start > end) return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    const stream = Readable.toWeb(createReadStream(path, { start, end })) as ReadableStream;
    return new Response(stream, { status: 206, headers: { ...headers, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(end - start + 1) } });
  }
  const stream = Readable.toWeb(createReadStream(path)) as ReadableStream;
  return new Response(stream, { headers: { ...headers, "Content-Length": String(size) } });
}
