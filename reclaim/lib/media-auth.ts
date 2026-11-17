import "server-only";
import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { createReadStream, statSync } from "node:fs";
import { Readable } from "node:stream";

/**
 * Short-lived signed links for private media (form-check videos). A page mints a token
 * bound to (viewer, resource, expiry) only after checking the viewer may see it; the
 * streaming route verifies the token and re-checks access. Mirrors a video host's signed
 * playback URLs, so moving storage to a host changes only this module and the route.
 */
const g = globalThis as unknown as { __mediaSecret?: string };
const SECRET = process.env.RECLAIM_MEDIA_SECRET ?? (g.__mediaSecret ??= randomBytes(32).toString("hex"));
const TTL_S = 60 * 60;

export function signMediaToken(viewerId: string, resource: string): string {
  const exp = Math.floor(Date.now() / 1000) + TTL_S;
  const payload = `${viewerId}.${resource}.${exp}`;
  const sig = createHmac("sha256", SECRET).update(payload).digest("base64url");
  return `${Buffer.from(payload).toString("base64url")}.${sig}`;
}

export function verifyMediaToken(token: string, resource: string): { viewerId: string } | null {
  const [p, sig] = token.split(".");
  if (!p || !sig) return null;
  const payload = Buffer.from(p, "base64url").toString();
  const expected = createHmac("sha256", SECRET).update(payload).digest();
  const given = Buffer.from(sig, "base64url");
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) return null;
  const [viewerId, res, exp] = payload.split(".");
  if (res !== resource || Number(exp) < Date.now() / 1000) return null;
  return { viewerId };
}

/** Stream a file with HTTP Range support (needed for seeking in <video>). */
export function streamFile(request: Request, path: string, type: string): Response {
  const size = statSync(path).size;
  const headers = { "Content-Type": type, "Accept-Ranges": "bytes", "Cache-Control": "private, no-store" };
  const range = request.headers.get("range");
  if (range) {
    const m = /bytes=(\d*)-(\d*)/.exec(range);
    const start = m?.[1] ? Number(m[1]) : 0;
    const end = m?.[2] ? Math.min(Number(m[2]), size - 1) : size - 1;
    if (start >= size || start > end) return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    const body = Readable.toWeb(createReadStream(path, { start, end })) as ReadableStream;
    return new Response(body, { status: 206, headers: { ...headers, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(end - start + 1) } });
  }
  return new Response(Readable.toWeb(createReadStream(path)) as ReadableStream, { headers: { ...headers, "Content-Length": String(size) } });
}
