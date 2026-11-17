import { NextResponse, type NextRequest } from "next/server";

/**
 * Runs before every page request (optimistic checks only; real authorisation happens in
 * requireUser() inside every protected page and server action).
 *  - SITE_PASSWORD set (any hosted copy of the prototype): the whole site sits behind one
 *    shared password (HTTP Basic auth), so demo logins and placeholder content aren't public.
 *  - Redirects signed-out visitors away from protected areas.
 *  - Issues a random first-party anonymous ID used for funnel measurement
 *    (no third-party identifiers, no fingerprinting).
 */
const PROTECTED = ["/portal", "/staff", "/admin"];

function passwordOk(request: NextRequest, expected: string): boolean {
  const header = request.headers.get("authorization") ?? "";
  if (!header.startsWith("Basic ")) return false;
  let decoded = "";
  try {
    decoded = atob(header.slice(6));
  } catch {
    return false;
  }
  const given = decoded.slice(decoded.indexOf(":") + 1);
  if (given.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < given.length; i++) diff |= given.charCodeAt(i) ^ expected.charCodeAt(i);
  return diff === 0;
}

export function proxy(request: NextRequest) {
  const sitePassword = process.env.SITE_PASSWORD;
  if (sitePassword && !passwordOk(request, sitePassword)) {
    return new NextResponse("RECLAIM prototype — password required.", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="RECLAIM prototype", charset="UTF-8"', "Cache-Control": "no-store" },
    });
  }

  const { pathname } = request.nextUrl;
  if (PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`)) && !request.cookies.get("rc_session")) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  const res = NextResponse.next();
  if (!request.cookies.get("rc_anon")) {
    res.cookies.set("rc_anon", crypto.randomUUID(), { httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 180 });
  }
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
