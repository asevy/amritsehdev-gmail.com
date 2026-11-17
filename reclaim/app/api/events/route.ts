import { isEventName, track } from "@/lib/analytics";
import { currentUser } from "@/lib/auth";

/** Client-side funnel events (assessment steps etc.). Names and property keys are allow-listed in lib/analytics.ts. */
export async function POST(request: Request) {
  let body: { name?: unknown; props?: Record<string, string | number | boolean | null> };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "bad json" }, { status: 400 });
  }
  if (!isEventName(body.name)) return Response.json({ error: "unknown event" }, { status: 400 });
  const user = await currentUser();
  await track(body.name, body.props ?? {}, user?.id);
  return Response.json({ ok: true });
}
