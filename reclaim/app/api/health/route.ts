/** Liveness check for the hosting platform. Deliberately outside the site password; returns no data. */
export function GET() {
  return new Response("ok", { headers: { "Cache-Control": "no-store" } });
}
