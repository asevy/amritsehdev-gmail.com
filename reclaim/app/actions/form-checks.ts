"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { requireUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { hasConsent, recordConsent } from "@/lib/consent";
import { track } from "@/lib/analytics";
import { createFormCheck, reviewFormCheck, deleteFormCheckVideo, deleteAllVideos, getFormCheck, FormCheckError } from "@/lib/form-checks";

export type CaptureState = { error?: string } | null;

/** Member records their own form check, or a coach records one with a member (in a session). */
export async function submitFormCheck(_prev: CaptureState, form: FormData): Promise<CaptureState> {
  const actor = await requireUser(["member", "coach"]);
  const memberId = actor.role === "coach" ? String(form.get("memberId") ?? "") : actor.id;
  if (actor.role === "coach") {
    const m = db("platform").prepare("SELECT role FROM users WHERE id = ?").get(memberId) as { role: string } | undefined;
    if (m?.role !== "member") return { error: "Choose a member." };
  }
  if (actor.role === "member" && form.get("consent") === "on" && !hasConsent(actor.id, "form_check_video")) {
    recordConsent(actor.id, "form_check_video", true, "/portal/form-checks");
  }
  const exercise = String(form.get("exercise") ?? "");
  const clip = form.get("clip");
  try {
    await createFormCheck(actor, {
      memberId,
      exercise,
      file: clip instanceof File && clip.size > 0 ? clip : null,
      metricsOnly: form.get("metricsOnly") === "on",
      note: String(form.get("note") ?? ""),
      mechanicsJson: String(form.get("mechanics") ?? ""),
    });
  } catch (e) {
    if (e instanceof FormCheckError) return { error: e.message };
    throw e;
  }
  await track("form_check_submitted", { kind: actor.role === "coach" ? "coach" : "member" }, actor.id);
  revalidatePath("/portal/form-checks");
  if (actor.role === "coach") redirect(`/staff/coach?m=${memberId}&saved=1`);
  redirect(`/portal/form-checks?saved=${encodeURIComponent(exercise)}#${encodeURIComponent(exercise)}`);
}

export async function submitReview(form: FormData) {
  const coach = await requireUser(["coach"]);
  const id = String(form.get("id"));
  const scores: Record<string, number> = {};
  for (const [k, v] of form.entries()) if (k.startsWith("score_")) scores[k.slice(6)] = Number(v);
  const fc = getFormCheck(id);
  try {
    reviewFormCheck(coach, id, scores, String(form.get("cues") ?? ""));
  } catch (e) {
    if (e instanceof FormCheckError) redirect(`/staff/coach?m=${fc?.user_id ?? ""}&fc=${id}&error=${encodeURIComponent(e.message)}`);
    throw e;
  }
  revalidatePath("/staff/coach");
  redirect(`/staff/coach?m=${fc!.user_id}&reviewed=1`);
}

export async function deleteFormCheckVideoAction(form: FormData) {
  const user = await requireUser(["member"]);
  try {
    deleteFormCheckVideo(user, String(form.get("id")), form.get("mode") === "all");
  } catch {}
  revalidatePath("/portal/form-checks");
  redirect("/portal/form-checks?deleted=1");
}

export async function deleteAllFormCheckVideosAction() {
  const user = await requireUser(["member"]);
  deleteAllVideos(user);
  revalidatePath("/portal/privacy");
  redirect("/portal/privacy?videos=deleted");
}
