"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireUser } from "@/lib/auth";
import {
  enrolAndSubmitIntake, bookEncounter, cancelEncounter, choosePharmacy, sendClinicalMessage, reportSideEffect,
} from "@/lib/clinical";
import { requestFill, payFill } from "@/lib/pharmacy";
import { PHARMACY_OPTIONS, type PharmacyChoice } from "@/config/partners";
import { sendEmail } from "@/lib/email";

const INTAKE_FIELDS = ["age_band", "current_symptoms", "pregnancy", "eating_disorder", "thyroid_history", "pancreatitis", "diabetes_type", "medications", "allergies", "visit_goals"];

export async function submitIntake(form: FormData) {
  const user = await requireUser(["member"]);
  if (form.get("ack_privacy") !== "on" || form.get("ack_virtual") !== "on" || form.get("ack_independence") !== "on") redirect("/portal/care?start=1&error=ack");
  const answers = Object.fromEntries(INTAKE_FIELDS.map((k) => [k, String(form.get(k) ?? "").slice(0, 1000)]));
  const flags = enrolAndSubmitIntake(user, answers, {
    legalName: String(form.get("legal_name") ?? user.name).slice(0, 120),
    dob: String(form.get("dob") ?? ""),
    hcnLast4: String(form.get("hcn_last4") ?? "").replace(/\D/g, "").slice(-4),
  });
  revalidatePath("/portal/care");
  redirect(flags.urgent.length ? "/portal/care?urgent=1" : "/portal/care?submitted=1");
}

export async function bookVisit(form: FormData) {
  const user = await requireUser(["member"]);
  try {
    bookEncounter(user, { startsAt: String(form.get("startsAt")), modality: form.get("modality") === "phone" ? "phone" : "video", locationAttested: form.get("attest") === "on" });
  } catch (e) {
    redirect(`/portal/care?error=${encodeURIComponent((e as Error).message)}`);
  }
  sendEmail({ to: user.email, userId: user.id, entity: "clinical", kind: "transactional", subject: "Your appointment with the medical practice", body: "Your virtual visit is booked. Details are in Care. This message is from the medical practice." });
  revalidatePath("/portal/care");
  redirect("/portal/care?booked=1#visits");
}

export async function cancelVisit(form: FormData) {
  const user = await requireUser(["member"]);
  cancelEncounter(user, String(form.get("id")));
  revalidatePath("/portal/care");
}

export async function choosePharmacyAction(form: FormData) {
  const user = await requireUser(["member"]);
  const choice = String(form.get("choice")) as PharmacyChoice;
  if (!PHARMACY_OPTIONS.some((o) => o.id === choice)) redirect("/portal/care?error=Choose%20an%20option#prescriptions");
  const detail = String(form.get("detail") ?? "").trim().slice(0, 200);
  if (choice === "other_pharmacy" && !detail) redirect("/portal/care?error=Tell%20us%20which%20pharmacy#prescriptions");
  const presented = String(form.get("presented") ?? "").split(",").filter(Boolean);
  try {
    choosePharmacy(user, String(form.get("rxId")), choice, detail, presented);
  } catch (e) {
    redirect(`/portal/care?error=${encodeURIComponent((e as Error).message)}#prescriptions`);
  }
  revalidatePath("/portal/care");
  redirect("/portal/care?chosen=1#prescriptions");
}

export async function requestFillAction(form: FormData) {
  const user = await requireUser(["member"]);
  try {
    requestFill(user, String(form.get("rxId")));
  } catch (e) {
    redirect(`/portal/care?error=${encodeURIComponent((e as Error).message)}#prescriptions`);
  }
  revalidatePath("/portal/care");
  redirect("/portal/care?filled=1#prescriptions");
}

export async function payFillAction(form: FormData) {
  const user = await requireUser(["member"]);
  try {
    payFill(user, String(form.get("fillId")));
  } catch (e) {
    redirect(`/portal/care?error=${encodeURIComponent((e as Error).message)}#prescriptions`);
  }
  sendEmail({ to: user.email, userId: user.id, entity: "pharmacy", kind: "transactional", subject: "Pharmacy receipt", body: "Receipt from your pharmacy for your prescription order. Prescription drugs are zero-rated for GST/HST." });
  revalidatePath("/portal/care");
  redirect("/portal/care?paid=1#prescriptions");
}

export async function sendClinicalMessageAction(form: FormData) {
  const user = await requireUser(["member"]);
  const body = String(form.get("body") ?? "").trim().slice(0, 4000);
  if (body) sendClinicalMessage(user, body);
  revalidatePath("/portal/care");
  redirect("/portal/care#messages");
}

export async function reportSideEffectAction(form: FormData) {
  const user = await requireUser(["member"]);
  const sev = String(form.get("severity"));
  const severity = (["mild", "moderate", "severe"].includes(sev) ? sev : "mild") as "mild" | "moderate" | "severe";
  const description = String(form.get("description") ?? "").trim().slice(0, 2000);
  if (description) reportSideEffect(user, description, severity);
  revalidatePath("/portal/care");
  redirect(`/portal/care?reported=${severity}#report`);
}
