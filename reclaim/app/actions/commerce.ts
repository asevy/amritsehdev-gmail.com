"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { requireUser } from "@/lib/auth";
import { buildCart, createPendingOrder, getOrder, completeOrder, cancelSubscription, pauseSubscription, resumeSubscription } from "@/lib/commerce";
import { getPaymentProvider } from "@/lib/payments";
import { addOnById } from "@/config/catalog";

export async function confirmOrder(form: FormData) {
  const user = await requireUser(["member"]);
  if (form.get("agree") !== "on") redirect(`/join/review?${new URLSearchParams(form.get("qs") as string).toString()}&error=agree`);
  const planId = String(form.get("plan") ?? "");
  const addOns = form.getAll("addons").map(String).filter((a) => !!addOnById(a));
  const cart = buildCart({ planId, addOnIds: addOns, province: user.province ?? "ON", sponsorCode: String(form.get("code") ?? "") || null });
  const orderId = createPendingOrder(user, cart);
  const provider = getPaymentProvider();
  const { redirectUrl } = await provider.createCheckout({ orderId, amountCents: cart.totalCents, customerEmail: user.email, description: `${cart.plan.name} membership` });
  redirect(redirectUrl);
}

/** Mock provider only: simulates the hosted payment page's success callback. */
export async function payMock(form: FormData) {
  const user = await requireUser(["member"]);
  const orderId = String(form.get("orderId") ?? "");
  const order = getOrder(orderId, user.id);
  if (!order) redirect("/portal");
  if (form.get("outcome") === "decline") redirect(`/checkout/${orderId}?declined=1`);
  await completeOrder(orderId, user, `mock_${Date.now()}`);
  redirect(`/join/welcome?order=${orderId}`);
}

export async function cancelMembership(form: FormData) {
  const user = await requireUser(["member"]);
  await cancelSubscription(user, String(form.get("reason") ?? "unspecified").slice(0, 60));
  revalidatePath("/portal/billing");
  redirect("/portal/billing?cancelled=1");
}

export async function pauseMembership() {
  const user = await requireUser(["member"]);
  await pauseSubscription(user);
  revalidatePath("/portal/billing");
  redirect("/portal/billing?paused=1");
}

export async function resumeMembership() {
  const user = await requireUser(["member"]);
  resumeSubscription(user);
  revalidatePath("/portal/billing");
  redirect("/portal/billing");
}
