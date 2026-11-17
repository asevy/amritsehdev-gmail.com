import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { randomBytes } from "node:crypto";
import { db, sha256, newId } from "./db";
import { hashPassword } from "./password";
export { verifyPassword } from "./password";

export type Role = "member" | "coach" | "clinician" | "pharmacist" | "admin";

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  province: string | null;
  patient_ref: string | null;
  sponsor_code: string | null;
  created_at: string;
}

const COOKIE = "rc_session";
const SESSION_DAYS = 14;

export async function createSession(userId: string): Promise<void> {
  const token = randomBytes(32).toString("base64url");
  const expires = new Date(Date.now() + SESSION_DAYS * 86400_000);
  db("platform").prepare("INSERT INTO sessions (id, user_id, expires_at) VALUES (?,?,?)").run(sha256(token), userId, expires.toISOString());
  const jar = await cookies();
  jar.set(COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    expires,
  });
}

export async function destroySession(): Promise<void> {
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  if (token) db("platform").prepare("DELETE FROM sessions WHERE id = ?").run(sha256(token));
  jar.delete(COOKIE);
}

export async function currentUser(): Promise<User | null> {
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  if (!token) return null;
  const row = db("platform")
    .prepare(
      `SELECT u.id, u.email, u.name, u.role, u.province, u.patient_ref, u.sponsor_code, u.created_at, s.expires_at
       FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ?`,
    )
    .get(sha256(token)) as (User & { expires_at: string }) | undefined;
  if (!row || new Date(row.expires_at) < new Date()) return null;
  const { expires_at: _e, ...user } = row;
  return user;
}

/** Use at the top of every protected page AND every server action (actions are reachable by direct POST). */
export async function requireUser(roles?: Role[]): Promise<User> {
  const user = await currentUser();
  if (!user) redirect("/login");
  if (roles && !roles.includes(user.role)) redirect(homeFor(user.role));
  return user;
}

export function homeFor(role: Role): string {
  switch (role) {
    case "member": return "/portal";
    case "coach": return "/staff/coach";
    case "clinician": return "/staff/clinician";
    case "pharmacist": return "/staff/pharmacy";
    case "admin": return "/admin";
  }
}

export function createUser(input: { email: string; password: string; name: string; role: Role; province?: string | null; sponsorCode?: string | null }): string {
  const id = newId("usr");
  const patientRef = input.role === "member" ? crypto.randomUUID() : null;
  db("platform")
    .prepare("INSERT INTO users (id, email, pw_hash, name, role, province, patient_ref, sponsor_code) VALUES (?,?,?,?,?,?,?,?)")
    .run(id, input.email.toLowerCase().trim(), hashPassword(input.password), input.name.trim(), input.role, input.province ?? null, patientRef, input.sponsorCode ?? null);
  return id;
}

// Simple in-memory login throttle (per process). Replace with a shared store in production.
const attempts = new Map<string, { n: number; until: number }>();
export function loginThrottled(key: string): boolean {
  const a = attempts.get(key);
  return !!a && a.n >= 5 && a.until > Date.now();
}
export function noteLoginFailure(key: string): void {
  const a = attempts.get(key) ?? { n: 0, until: 0 };
  a.n += 1;
  a.until = Date.now() + 10 * 60_000;
  attempts.set(key, a);
}
export function clearLoginFailures(key: string): void {
  attempts.delete(key);
}
