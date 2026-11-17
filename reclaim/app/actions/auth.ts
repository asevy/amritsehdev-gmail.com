"use server";

import { redirect } from "next/navigation";
import { headers } from "next/headers";
import { db, audit } from "@/lib/db";
import {
  createSession, destroySession, verifyPassword, homeFor, createUser, currentUser,
  loginThrottled, noteLoginFailure, clearLoginFailures, type Role,
} from "@/lib/auth";
import { recordConsent } from "@/lib/consent";
import { track } from "@/lib/analytics";
import { LIVE_CODES } from "@/config/site";
import { planById, addOnById } from "@/config/catalog";
import { sponsorFor } from "@/lib/commerce";

export type AuthState = { error?: string } | null;

export async function login(_prev: AuthState, form: FormData): Promise<AuthState> {
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const password = String(form.get("password") ?? "");
  const ip = (await headers()).get("x-forwarded-for") ?? "local";
  const key = `${email}|${ip}`;
  if (loginThrottled(key)) return { error: "Too many attempts. Try again in 10 minutes." };
  const row = db("platform").prepare("SELECT id, pw_hash, role FROM users WHERE email = ?").get(email) as { id: string; pw_hash: string; role: Role } | undefined;
  if (!row || !verifyPassword(password, row.pw_hash)) {
    noteLoginFailure(key);
    return { error: "Email or password is incorrect." };
  }
  clearLoginFailures(key);
  await createSession(row.id);
  audit("platform", { actorId: row.id, actorRole: row.role, subjectUser: row.id, action: "auth.login" });
  const next = String(form.get("next") ?? "");
  redirect(next.startsWith("/") && !next.startsWith("//") ? next : homeFor(row.role));
}

export async function logout() {
  await destroySession();
  redirect("/");
}

/**
 * Join step 2: create an account with separate, unbundled consents, then continue to
 * order review (memberships) or straight to the portal's Care area (medical-only path).
 */
export async function createAccount(_prev: AuthState, form: FormData): Promise<AuthState> {
  const path = String(form.get("path") ?? "membership");
  const planId = String(form.get("plan") ?? "");
  const addOns = form.getAll("addons").map(String).filter((a) => !!addOnById(a));
  const code = String(form.get("code") ?? "").trim().toUpperCase();
  const province = String(form.get("province") ?? "");
  if (path === "membership" && !planById(planId)) return { error: "Choose a programme." };
  if (!LIVE_CODES.includes(province)) redirect(`/waitlist?j=${encodeURIComponent(province)}`);
  if (code && !sponsorFor(code)) return { error: "That sponsor code isn't valid." };

  let user = await currentUser();
  if (!user) {
    const name = String(form.get("name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");
    if (!name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { error: "Enter your name and a valid email." };
    if (password.length < 10) return { error: "Use a password of at least 10 characters." };
    if (form.get("terms") !== "on" || form.get("privacy") !== "on") return { error: "Please accept the terms and privacy notice to create an account." };
    if (db("platform").prepare("SELECT 1 FROM users WHERE email = ?").get(email)) return { error: "An account with that email exists — log in instead." };
    const id = createUser({ email, password, name, role: "member", province, sponsorCode: code || null });
    recordConsent(id, "platform_terms", true, "/join");
    recordConsent(id, "platform_privacy", true, "/join");
    recordConsent(id, "marketing_email", form.get("marketing") === "on", "/join");
    recordConsent(id, "product_analytics", form.get("analytics") === "on", "/join");
    if (code) recordConsent(id, "employer_aggregate", form.get("employer_ack") === "on", "/join");
    await createSession(id);
    await track("account_created", { plan: planId || "medical_only" }, id);

    // Assessment answers move from the browser into the account only now, as Blueprint v1 (coaching data).
    const assessment = String(form.get("assessment") ?? "");
    if (assessment) {
      try {
        const parsed = JSON.parse(assessment);
        if (parsed?.answers) {
          db("platform").prepare("INSERT INTO blueprints (user_id, version, data_json, source, author) VALUES (?,?,?,?,?)")
            .run(id, 1, JSON.stringify({ fromAssessment: parsed.answers, suggested: parsed.result?.plan ?? null }), "assessment", "Free assessment");
        }
      } catch {}
    }
    user = await currentUser();
  }
  if (path === "medical") redirect("/portal/care?start=1");
  const qs = new URLSearchParams({ plan: planId });
  addOns.forEach((a) => qs.append("addons", a));
  if (code) qs.set("code", code);
  redirect(`/join/review?${qs.toString()}`);
}
