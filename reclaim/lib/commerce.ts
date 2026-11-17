import "server-only";
import { db, newId, nowIso, sha256, getSetting, audit } from "./db";
import { ADD_ONS, planById, planPrice, type Plan } from "@/config/catalog";
import { ENTITIES } from "@/config/site";
import { taxFor, TAX_RATES } from "@/config/tax";
import { sendEmail } from "./email";
import { track } from "./analytics";
import { cadExact, fmtDate } from "./money";
import type { User } from "./auth";

export interface CartLine {
  sku: string;
  kind: "plan" | "addon";
  description: string;
  qty: number;
  unitCents: number;
  taxCode: "taxable_service" | "taxable_goods";
  taxCents: number;
}
export interface Cart {
  plan: Plan;
  lines: CartLine[];
  province: string;
  variant: number;
  sponsor: { code: string; org: string } | null;
  subtotalCents: number;
  taxCents: number;
  totalCents: number;
  taxLabel: string;
  renewalCents: number; // what the next monthly charge will be (plan only)
}

/** Sequential price test: one live price per offer at a time, switched by an admin. */
export function activeVariant(): number {
  return getSetting("price_variant", "0") === "1" ? 1 : 0;
}

export function sponsorFor(code: string | null | undefined) {
  if (!code) return null;
  return (db("platform").prepare("SELECT code, org_name, plan_id FROM sponsors WHERE code = ?").get(code.trim().toUpperCase()) as
    | { code: string; org_name: string; plan_id: string }
    | undefined) ?? null;
}

export function buildCart(input: { planId: string; addOnIds: string[]; province: string; sponsorCode?: string | null }): Cart {
  const plan = planById(input.planId);
  if (!plan) throw new Error("Unknown plan");
  if (!TAX_RATES[input.province]) throw new Error("Province not supported");
  const variant = activeVariant();
  const sponsor = sponsorFor(input.sponsorCode);
  const sponsored = !!sponsor && sponsor.plan_id === plan.id;
  const lines: CartLine[] = [];
  const planCents = sponsored ? 0 : planPrice(plan, variant);
  lines.push({
    sku: `plan:${plan.id}`,
    kind: "plan",
    description: `${plan.name} membership — first month${sponsored ? ` (sponsored by ${sponsor!.org_name})` : ""}`,
    qty: 1,
    unitCents: planCents,
    taxCode: "taxable_service",
    taxCents: taxFor("taxable_service", input.province, planCents).cents,
  });
  for (const id of input.addOnIds) {
    const a = ADD_ONS.find((x) => x.id === id);
    if (!a) continue;
    if (a.id === "blueprint-session" && plan.workload.blueprintMinutesOnce > 0) continue; // already included
    lines.push({
      sku: `addon:${a.id}`,
      kind: "addon",
      description: a.name,
      qty: 1,
      unitCents: a.priceCents,
      taxCode: "taxable_service",
      taxCents: taxFor(a.taxCode, input.province, a.priceCents).cents,
    });
  }
  const subtotal = lines.reduce((s, l) => s + l.unitCents * l.qty, 0);
  const tax = lines.reduce((s, l) => s + l.taxCents, 0);
  const renewal = planCents + taxFor("taxable_service", input.province, planCents).cents;
  return {
    plan,
    lines,
    province: input.province,
    variant,
    sponsor: sponsored ? { code: sponsor!.code, org: sponsor!.org_name } : null,
    subtotalCents: subtotal,
    taxCents: tax,
    totalCents: subtotal + tax,
    taxLabel: TAX_RATES[input.province].label,
    renewalCents: renewal,
  };
}

/**
 * Pre-contract disclosure (Ontario Consumer Protection Act, 2002 — CPA 2023 is not
 * in force as of 2026-11). A coaching membership is likely a "personal development
 * service" (CPA 2002 ss.29–31; O. Reg. 17/05): 10-day cooling-off, term ≤ 1 year,
 * instalment option, and trust rules for advance payments before services are
 * available. Counsel to confirm; we disclose to the stricter of that regime and the
 * internet-agreement rules. The exact snapshot shown before the customer agrees is
 * stored (with a SHA-256 fingerprint) and a copy is emailed immediately.
 */
export function agreementSnapshot(cart: Cart, user: { name: string; email: string }) {
  const e = ENTITIES.platform;
  const start = new Date();
  const renew = new Date(start);
  renew.setMonth(renew.getMonth() + 1);
  return {
    supplier: { legalName: e.legalName, tradeName: e.displayName, address: e.address, email: e.email, phone: e.phone },
    customer: { name: user.name, email: user.email },
    description: cart.plan.includes.concat(cart.plan.limits),
    lines: cart.lines.map((l) => ({ description: l.description, amount: cadExact(l.unitCents), tax: cadExact(l.taxCents) })),
    subtotal: cadExact(cart.subtotalCents),
    tax: `${cadExact(cart.taxCents)} (${cart.taxLabel})`,
    total: cadExact(cart.totalCents),
    currency: "CAD",
    startDate: fmtDate(start.toISOString()),
    renewal: cart.sponsor
      ? `Sponsored by ${cart.sponsor.org}. Your employer pays monthly while you remain eligible; you will not be charged.`
      : `Renews automatically every month on the same date (next: ${fmtDate(renew.toISOString())}) at ${cadExact(cart.renewalCents)} including tax, until you cancel.`,
    cancellation:
      "Cancel online any time in Billing in two clicks or fewer. Cancellation takes effect at the end of the current paid month; there is no cancellation fee. You can pause instead for up to one month.",
    refunds:
      "Ontario law may give you a 10-day cooling-off period to cancel for a full refund; RECLAIM extends this to 14 days after your first payment. After that, cancelling stops future charges. Unused add-ons are refundable on request. Refunds never depend on any clinical decision.",
    notIncluded:
      "Medical services are provided and billed (if at all) by the independent medical practice; OHIP-insured services are never charged to you. Medication is sold by the pharmacy you choose.",
    agreedAt: null as string | null,
  };
}

export function createPendingOrder(user: User, cart: Cart): string {
  const snapshot = agreementSnapshot(cart, user);
  snapshot.agreedAt = nowIso();
  const json = JSON.stringify(snapshot);
  const id = newId("ord");
  const d = db("platform");
  d.prepare(
    `INSERT INTO orders (id, user_id, status, province, subtotal_cents, tax_cents, total_cents, price_variant, sponsor_code, agreement_json, agreement_sha, provider)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
  ).run(id, user.id, "pending", cart.province, cart.subtotalCents, cart.taxCents, cart.totalCents, cart.variant, cart.sponsor?.code ?? null, json, sha256(json), "mock");
  const ins = d.prepare("INSERT INTO order_lines (order_id, sku, kind, description, qty, unit_cents, tax_code, tax_cents) VALUES (?,?,?,?,?,?,?,?)");
  for (const l of cart.lines) ins.run(id, l.sku, l.kind, l.description, l.qty, l.unitCents, l.taxCode, l.taxCents);
  return id;
}

export function getOrder(orderId: string, userId: string) {
  const order = db("platform").prepare("SELECT * FROM orders WHERE id = ? AND user_id = ?").get(orderId, userId) as
    | { id: string; status: string; total_cents: number; tax_cents: number; subtotal_cents: number; province: string; agreement_json: string; agreement_sha: string; created_at: string; paid_at: string | null; price_variant: number; sponsor_code: string | null }
    | undefined;
  if (!order) return null;
  const lines = db("platform").prepare("SELECT * FROM order_lines WHERE order_id = ?").all(orderId) as Array<{ sku: string; kind: string; description: string; unit_cents: number; tax_cents: number; qty: number }>;
  return { ...order, lines };
}

/** Called by the payment provider on success (mock: our test checkout page; production: a verified webhook). */
export async function completeOrder(orderId: string, user: User, providerRef: string): Promise<void> {
  const d = db("platform");
  const order = getOrder(orderId, user.id);
  if (!order) throw new Error("Order not found");
  if (order.status !== "pending") return; // idempotent
  const paidAt = nowIso();
  d.prepare("UPDATE orders SET status = 'paid', paid_at = ?, provider_ref = ? WHERE id = ?").run(paidAt, providerRef, orderId);

  for (const l of order.lines) {
    if (l.kind === "plan") {
      const planId = l.sku.split(":")[1];
      const periodEnd = new Date();
      periodEnd.setMonth(periodEnd.getMonth() + 1);
      d.prepare("UPDATE subscriptions SET status = 'cancelled', cancelled_at = ?, cancel_reason = 'replaced' WHERE user_id = ? AND status <> 'cancelled'").run(paidAt, user.id);
      d.prepare(
        `INSERT INTO subscriptions (id, user_id, plan_id, status, price_cents, price_variant, sponsored, order_id, started_at, current_period_end)
         VALUES (?,?,?,?,?,?,?,?,?,?)`,
      ).run(newId("sub"), user.id, planId, "active", l.unit_cents, order.price_variant, order.sponsor_code ? 1 : 0, orderId, paidAt, periodEnd.toISOString());
      const plan = planById(planId);
      if (plan && plan.creditsPerMonth > 0) {
        const exp = new Date();
        exp.setMonth(exp.getMonth() + 2);
        d.prepare("INSERT INTO credits_ledger (user_id, delta, reason, ref, expires_at) VALUES (?,?,?,?,?)").run(user.id, plan.creditsPerMonth, `${plan.name} monthly credits`, orderId, exp.toISOString());
      }
    } else {
      const addOn = ADD_ONS.find((a) => `addon:${a.id}` === l.sku);
      if (addOn?.credits) {
        const exp = new Date(Date.now() + 90 * 86400_000);
        d.prepare("INSERT INTO credits_ledger (user_id, delta, reason, ref, expires_at) VALUES (?,?,?,?,?)").run(user.id, addOn.credits, addOn.name, orderId, exp.toISOString());
      }
    }
  }

  const agreement = JSON.parse(order.agreement_json);
  sendEmail({
    to: user.email,
    userId: user.id,
    entity: "platform",
    kind: "transactional",
    subject: "Your RECLAIM receipt and membership agreement",
    body: [
      `Thank you, ${user.name}.`,
      ``,
      `Receipt — ${ENTITIES.platform.legalName}`,
      ...order.lines.map((l) => `  ${l.description}: ${cadExact(l.unit_cents)} + tax ${cadExact(l.tax_cents)}`),
      `  Total charged: ${cadExact(order.total_cents)} CAD`,
      ``,
      `Copy of your agreement (fingerprint ${order.agreement_sha.slice(0, 12)}):`,
      `  Renewal: ${agreement.renewal}`,
      `  Cancellation: ${agreement.cancellation}`,
      `  Refunds: ${agreement.refunds}`,
      `  Not included: ${agreement.notIncluded}`,
    ].join("\n"),
  });
  audit("platform", { actorId: user.id, actorRole: user.role, subjectUser: user.id, action: "order.paid", resource: orderId });
  await track("order_paid", { plan: order.lines.find((l) => l.kind === "plan")?.sku ?? null, variant: order.price_variant }, user.id);
}

export function activeSubscription(userId: string) {
  return (db("platform")
    .prepare("SELECT * FROM subscriptions WHERE user_id = ? AND status <> 'cancelled' ORDER BY started_at DESC LIMIT 1")
    .get(userId) as
    | { id: string; plan_id: string; status: string; price_cents: number; price_variant: number; sponsored: number; order_id: string; started_at: string; current_period_end: string; cancel_at_period_end: number; paused_until: string | null }
    | undefined) ?? null;
}

export function refundEligibility(userId: string): { eligible: boolean; orderId?: string; amountCents?: number; rule: string } {
  const sub = activeSubscription(userId);
  if (!sub) return { eligible: false, rule: "no_active_subscription" };
  const first = db("platform").prepare("SELECT id, total_cents, paid_at FROM orders WHERE user_id = ? AND status = 'paid' ORDER BY paid_at ASC LIMIT 1").get(userId) as
    | { id: string; total_cents: number; paid_at: string }
    | undefined;
  if (!first) return { eligible: false, rule: "no_paid_order" };
  const days = (Date.now() - new Date(first.paid_at).getTime()) / 86400_000;
  if (first.id === sub.order_id && days <= 14 && first.total_cents > 0)
    return { eligible: true, orderId: first.id, amountCents: first.total_cents, rule: "first_payment_within_14_days" };
  return { eligible: false, rule: "outside_14_day_window" };
}

export async function cancelSubscription(user: User, reason: string): Promise<{ refundedCents: number }> {
  const sub = activeSubscription(user.id);
  if (!sub) return { refundedCents: 0 };
  const d = db("platform");
  const refund = refundEligibility(user.id);
  let refunded = 0;
  if (refund.eligible && refund.orderId) {
    d.prepare("INSERT INTO refunds (order_id, amount_cents, policy_rule) VALUES (?,?,?)").run(refund.orderId, refund.amountCents ?? 0, refund.rule);
    d.prepare("UPDATE orders SET status = 'refunded' WHERE id = ?").run(refund.orderId);
    d.prepare("UPDATE subscriptions SET status = 'cancelled', cancelled_at = ?, cancel_reason = ? WHERE id = ?").run(nowIso(), reason, sub.id);
    refunded = refund.amountCents!;
  } else {
    d.prepare("UPDATE subscriptions SET cancel_at_period_end = 1, cancel_reason = ? WHERE id = ?").run(reason, sub.id);
  }
  sendEmail({
    to: user.email,
    userId: user.id,
    entity: "platform",
    kind: "transactional",
    subject: "Your RECLAIM membership has been cancelled",
    body: refunded
      ? `Your membership is cancelled and ${cadExact(refunded)} has been refunded to your original payment method. Your medical care with the independent practice and any prescriptions are not affected.`
      : `Your membership will end on ${fmtDate(sub.current_period_end)} and you will not be charged again. Your medical care with the independent practice and any prescriptions are not affected.`,
  });
  audit("platform", { actorId: user.id, actorRole: user.role, subjectUser: user.id, action: "subscription.cancelled", resource: sub.id });
  await track("subscription_cancelled", { reason, plan: sub.plan_id }, user.id);
  return { refundedCents: refunded };
}

export function resumeSubscription(user: User) {
  const sub = activeSubscription(user.id);
  if (!sub) return;
  db("platform").prepare("UPDATE subscriptions SET cancel_at_period_end = 0, cancel_reason = NULL, status = 'active', paused_until = NULL WHERE id = ?").run(sub.id);
  audit("platform", { actorId: user.id, actorRole: user.role, subjectUser: user.id, action: "subscription.resumed", resource: sub.id });
}

export async function pauseSubscription(user: User) {
  const sub = activeSubscription(user.id);
  if (!sub) return;
  const until = new Date(sub.current_period_end);
  until.setMonth(until.getMonth() + 1);
  db("platform").prepare("UPDATE subscriptions SET status = 'paused', paused_until = ? WHERE id = ?").run(until.toISOString(), sub.id);
  sendEmail({ to: user.email, userId: user.id, entity: "platform", kind: "transactional", subject: "Your RECLAIM membership is paused", body: `No charge will be taken until ${fmtDate(until.toISOString())}. Your library and saved data stay available.` });
  await track("subscription_paused", { plan: sub.plan_id }, user.id);
}

export function creditBalance(userId: string): number {
  const row = db("platform")
    .prepare("SELECT COALESCE(SUM(delta),0) AS n FROM credits_ledger WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ? OR delta < 0)")
    .get(userId, nowIso()) as { n: number };
  return Math.max(0, row.n);
}
