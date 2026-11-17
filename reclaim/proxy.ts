import { NextResponse, type NextRequest } from "next/server";

/**
 * Optimistic checks only (per Next.js guidance). Real authorisation happens in
 * requireUser() inside every protected page and server action.
 *  - Redirects signed-out visitors away from protected areas.
 *  - Issues a random first-party anonymous ID used for funnel measurement
 *    (no third-party identifiers, no fingerprinting).
 */
const PROTECTED = ["/portal", "/staff", "/admin"];

export function proxy(request: NextRequest) {
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
  matcher: ["/((?!_next/static|_next/image|media/|favicon.ico).*)"],
};
