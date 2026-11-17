"use server";

import { db, sha256 } from "@/lib/db";
import { track } from "@/lib/analytics";
import { JURISDICTIONS } from "@/config/site";
import { CONSENTS } from "@/config/consents";

export type FormState = { ok: boolean; message: string } | null;

const email = (v: FormDataEntryValue | null) => {
  const s = String(v ?? "").trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s) ? s : null;
};

export async function joinWaitlist(_prev: FormState, form: FormData): Promise<FormState> {
  const e = email(form.get("email"));
  const jurisdiction = String(form.get("jurisdiction") ?? "");
  if (!e) return { ok: false, message: "Enter a valid email address." };
  if (!JURISDICTIONS.some((j) => j.code === jurisdiction)) return { ok: false, message: "Choose where you live." };
  // Data minimisation: keep only the first three characters of a postal code (FSA) or a US state code.
  const fsa = String(form.get("fsa") ?? "").trim().toUpperCase().replace(/\s/g, "").slice(0, 3) || null;
  const interests = form.getAll("interests").map(String).filter((x) => ["coaching", "medical", "local", "employer"].includes(x));
  const marketing = form.get("marketing") === "on";
  db("platform")
    .prepare("INSERT INTO waitlist (email, jurisdiction, fsa, interests_json, marketing_consent, consent_text_sha) VALUES (?,?,?,?,?,?)")
    .run(e, jurisdiction, fsa, JSON.stringify(interests), marketing ? 1 : 0, marketing ? sha256(CONSENTS.marketing_email.text) : null);
  await track("waitlist_joined", { jurisdiction });
  return {
    ok: true,
    message: marketing
      ? "You're on the list. We'll email you when RECLAIM opens where you live."
      : "You're on the list. Because you didn't opt in to email, we'll only contact you once — when RECLAIM opens where you live.",
  };
}

export async function submitLead(_prev: FormState, form: FormData): Promise<FormState> {
  const kind = String(form.get("kind") ?? "");
  if (!["employer", "enterprise", "partner", "research"].includes(kind)) return { ok: false, message: "Unknown form." };
  const e = email(form.get("email"));
  const org = String(form.get("org") ?? "").trim().slice(0, 120);
  const name = String(form.get("name") ?? "").trim().slice(0, 120);
  if (!e || !org || !name) return { ok: false, message: "Please complete your name, organisation and work email." };
  db("platform")
    .prepare("INSERT INTO leads (kind, org, name, email, size, message) VALUES (?,?,?,?,?,?)")
    .run(kind, org, name, e, String(form.get("size") ?? "").slice(0, 40), String(form.get("message") ?? "").slice(0, 2000));
  await track("lead_submitted", { kind });
  return { ok: true, message: "Thanks — a founder will reply within two business days. We haven't added you to any mailing list." };
}

export async function submitWtp(_prev: FormState, form: FormData): Promise<FormState> {
  const vals = ["too_cheap", "cheap", "expensive", "too_expensive"].map((k) => Math.round(Number(form.get(k))));
  if (vals.some((v) => !Number.isFinite(v) || v < 0 || v > 5000)) return { ok: false, message: "Enter four monthly amounts in dollars." };
  const [tc, c, ex, tx] = vals;
  if (!(tc <= c && c <= ex && ex <= tx)) return { ok: false, message: "The four amounts should go from lowest to highest." };
  const { cookies } = await import("next/headers");
  const anon = (await cookies()).get("rc_anon")?.value ?? null;
  db("platform").prepare("INSERT INTO wtp_responses (anon_id, too_cheap, cheap, expensive, too_expensive) VALUES (?,?,?,?,?)").run(anon, tc, c, ex, tx);
  return { ok: true, message: "Thank you — recorded anonymously." };
}

export async function fakeDoor(door: string) {
  await track("fake_door_clicked", { door });
}
