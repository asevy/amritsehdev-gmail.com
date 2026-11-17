import "server-only";
import { db } from "./db";
import { hasConsent } from "./consent";
import type { EntityId } from "@/config/site";

/**
 * Email adapter. In this prototype every email is written to an outbox table
 * (visible in Admin → Outbox) instead of being sent.
 *
 * CASL guard: commercial messages are refused unless the recipient currently
 * holds the marketing_email consent, and always carry sender identification and
 * an unsubscribe instruction. Transactional messages (receipts, agreement copies,
 * appointment notices) do not require marketing consent.
 */
export function sendEmail(input: {
  to: string;
  userId?: string | null;
  entity: EntityId;
  kind: "transactional" | "commercial";
  subject: string;
  body: string;
}): { sent: boolean; reason?: string } {
  if (input.kind === "commercial") {
    if (!input.userId || !hasConsent(input.userId, "marketing_email")) return { sent: false, reason: "no CASL consent" };
    input.body += "\n\n—\nSent by RECLAIM, [registered address]. Unsubscribe any time: reply STOP or visit Privacy settings.";
  }
  db("platform")
    .prepare("INSERT INTO email_outbox (to_email, user_id, entity_id, class, subject, body) VALUES (?,?,?,?,?,?)")
    .run(input.to, input.userId ?? null, input.entity, input.kind, input.subject, input.body);
  return { sent: true };
}
