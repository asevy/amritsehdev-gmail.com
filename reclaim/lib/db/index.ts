import "server-only";
import { DatabaseSync } from "node:sqlite";
import { readFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { createHash, randomBytes } from "node:crypto";
import { seedDemoData } from "./seed";

/**
 * Three physically separate stores, one per legal entity:
 *   platform  — RECLAIM commercial company (PIPEDA)
 *   clinical  — independent medical practice (PHIPA custodian; stands in for its EMR)
 *   pharmacy  — licensed pharmacy (PHIPA custodian; stands in for its dispensing system)
 * They share no tables and no joins; the only link is users.patient_ref.
 *
 * Only lib/clinical/** may open the clinical store and only lib/pharmacy/** the pharmacy
 * store — scripts/compliance-lint.mjs enforces this import boundary.
 */
export type Store = "platform" | "clinical" | "pharmacy";

const DATA_DIR = process.env.RECLAIM_DATA_DIR ?? join(process.cwd(), ".data");

type Registry = { dbs: Partial<Record<Store, DatabaseSync>>; seeded: boolean };
const g = globalThis as unknown as { __reclaimDb?: Registry };
const registry: Registry = (g.__reclaimDb ??= { dbs: {}, seeded: false });

function open(store: Store): DatabaseSync {
  mkdirSync(DATA_DIR, { recursive: true });
  const db = new DatabaseSync(join(DATA_DIR, `${store}.db`));
  db.exec("PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 3000;");
  db.exec(readFileSync(join(process.cwd(), "db/schema", `${store}.sql`), "utf8"));
  return db;
}

export function db(store: Store): DatabaseSync {
  let handle = registry.dbs[store];
  if (!handle) {
    handle = open(store);
    registry.dbs[store] = handle;
  }
  if (!registry.seeded) {
    registry.seeded = true;
    // First connection on an empty database seeds demo data so `npm run dev` works on a fresh clone.
    const platform = store === "platform" ? handle : db("platform");
    const count = platform.prepare("SELECT COUNT(*) AS n FROM users").get() as { n: number };
    if (count.n === 0) seedDemoData();
  }
  return handle;
}

export function newId(prefix: string): string {
  return `${prefix}_${randomBytes(9).toString("base64url")}`;
}

export const nowIso = () => new Date().toISOString();

export function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

/** Append a hash-chained audit entry to a store's audit_log. */
export function audit(
  store: Store,
  entry: { actorId?: string | null; actorRole?: string | null; subjectUser?: string | null; action: string; resource?: string | null },
): void {
  const d = db(store);
  const prev = d.prepare("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").get() as { hash: string } | undefined;
  const prevHash = prev?.hash ?? "GENESIS";
  const createdAt = nowIso();
  const payload = JSON.stringify([prevHash, entry.actorId ?? null, entry.actorRole ?? null, entry.subjectUser ?? null, entry.action, entry.resource ?? null, createdAt]);
  d.prepare(
    "INSERT INTO audit_log (actor_id, actor_role, subject_user, action, resource, created_at, prev_hash, hash) VALUES (?,?,?,?,?,?,?,?)",
  ).run(entry.actorId ?? null, entry.actorRole ?? null, entry.subjectUser ?? null, entry.action, entry.resource ?? null, createdAt, prevHash, sha256(payload));
}

/** Verify the hash chain of a store's audit log. Returns the first broken row id, or null if intact. */
export function verifyAuditChain(store: Store): number | null {
  const rows = db(store).prepare("SELECT * FROM audit_log ORDER BY id").all() as Array<Record<string, string | number | null>>;
  let prev = "GENESIS";
  for (const r of rows) {
    const payload = JSON.stringify([prev, r.actor_id, r.actor_role, r.subject_user, r.action, r.resource, r.created_at]);
    if (r.prev_hash !== prev || r.hash !== sha256(payload)) return Number(r.id);
    prev = String(r.hash);
  }
  return null;
}

export function getSetting(key: string, fallback: string): string {
  const row = db("platform").prepare("SELECT value FROM settings WHERE key = ?").get(key) as { value: string } | undefined;
  return row?.value ?? fallback;
}
export function setSetting(key: string, value: string): void {
  db("platform").prepare("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value").run(key, value);
}
