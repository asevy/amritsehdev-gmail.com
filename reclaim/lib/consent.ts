import "server-only";
import { db, sha256 } from "./db";
import { CONSENTS, type ConsentKind } from "@/config/consents";

export function recordConsent(userId: string, kind: ConsentKind, granted: boolean, route: string): void {
  const def = CONSENTS[kind];
  db("platform")
    .prepare("INSERT INTO consents (user_id, kind, granted, version, text_sha, route) VALUES (?,?,?,?,?,?)")
    .run(userId, kind, granted ? 1 : 0, def.version, sha256(def.text), route);
}

export function currentConsents(userId: string): Record<ConsentKind, boolean> {
  const rows = db("platform")
    .prepare(
      `SELECT kind, granted FROM consents c
       WHERE user_id = ? AND id = (SELECT MAX(id) FROM consents WHERE user_id = c.user_id AND kind = c.kind)`,
    )
    .all(userId) as Array<{ kind: ConsentKind; granted: number }>;
  const out = Object.fromEntries(Object.keys(CONSENTS).map((k) => [k, false])) as Record<ConsentKind, boolean>;
  for (const r of rows) out[r.kind] = r.granted === 1;
  return out;
}

export function hasConsent(userId: string, kind: ConsentKind): boolean {
  return currentConsents(userId)[kind];
}

export function consentHistory(userId: string) {
  return db("platform")
    .prepare("SELECT kind, granted, version, text_sha, route, created_at FROM consents WHERE user_id = ? ORDER BY id DESC")
    .all(userId) as Array<{ kind: ConsentKind; granted: number; version: string; text_sha: string; route: string; created_at: string }>;
}
