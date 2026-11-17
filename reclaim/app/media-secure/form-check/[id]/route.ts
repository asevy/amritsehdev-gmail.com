import { existsSync } from "node:fs";
import { verifyMediaToken, streamFile } from "@/lib/media-auth";
import { getFormCheck, canView, filePathFor } from "@/lib/form-checks";
import { db } from "@/lib/db";

/** Streams a form-check video after verifying the signed token AND re-checking the viewer's access. */
export async function GET(request: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const claims = verifyMediaToken(new URL(request.url).searchParams.get("t") ?? "", `fc:${id}`);
  if (!claims) return new Response("Link expired — reload the page", { status: 403 });
  const viewer = db("platform").prepare("SELECT id, role FROM users WHERE id = ?").get(claims.viewerId) as { id: string; role: string } | undefined;
  const fc = getFormCheck(id);
  if (!viewer || !fc || !canView(viewer, fc)) return new Response("Not available", { status: 403 });
  const path = filePathFor(fc);
  if (!path || !existsSync(path)) return new Response("Video deleted", { status: 404 });
  return streamFile(request, path, fc.mime ?? "video/mp4");
}
