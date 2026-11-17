import { currentUser } from "@/lib/auth";
import { db, audit } from "@/lib/db";
import { getEnrolment, exportClinicalSummaryForPatient } from "@/lib/clinical";

/** Self-serve export of everything RECLAIM (platform) holds about the member, plus a labelled clinical summary. */
export async function GET() {
  const user = await currentUser();
  if (!user || user.role !== "member") return new Response("Unauthorised", { status: 401 });
  const d = db("platform");
  const q = (sql: string) => d.prepare(sql).all(user.id);
  const data = {
    exportedAt: new Date().toISOString(),
    controller: "RECLAIM (platform company) — PIPEDA",
    account: { id: user.id, name: user.name, email: user.email, province: user.province, createdAt: user.created_at },
    consents: q("SELECT kind, granted, version, text_sha, route, created_at FROM consents WHERE user_id = ? ORDER BY id"),
    blueprints: q("SELECT version, source, author, created_at, data_json FROM blueprints WHERE user_id = ? ORDER BY version").map((r) => ({ ...(r as object), data: JSON.parse(String((r as { data_json: string }).data_json)), data_json: undefined })),
    measurements: q("SELECT metric, value, unit, source, measured_at, note FROM measurements WHERE user_id = ? ORDER BY measured_at"),
    planItems: q("SELECT week_start, day, kind, title, detail, done_at FROM plan_items WHERE user_id = ?"),
    formChecks: (q("SELECT id, exercise, recorded_by, member_note, mechanics_json, status, created_at, reviewed_at, scores_json, cues, file_path FROM form_checks WHERE user_id = ? AND status <> 'deleted' ORDER BY created_at") as Array<Record<string, unknown>>)
      .map(({ mechanics_json, scores_json, file_path, ...r }) => ({ ...r, mechanics: mechanics_json ? JSON.parse(String(mechanics_json)) : null, scores: scores_json ? JSON.parse(String(scores_json)) : null, videoStored: !!file_path })),
    formCheckVideosNote: "Videos are not embedded in this file; download each from Form checks, or ask support for a bundle.",
    bookings: q("SELECT kind, title, starts_at, status, credits_used FROM bookings WHERE user_id = ?"),
    coachMessages: q("SELECT sender_name, body, created_at FROM messages WHERE user_id = ? ORDER BY id"),
    credits: q("SELECT delta, reason, created_at FROM credits_ledger WHERE user_id = ?"),
    orders: q("SELECT id, status, total_cents, tax_cents, paid_at, agreement_json FROM orders WHERE user_id = ?"),
    medicalPractice: getEnrolment(user) ? { custodian: "Independent medical practice — PHIPA", ...exportClinicalSummaryForPatient(user) } : null,
  };
  audit("platform", { actorId: user.id, actorRole: "member", subjectUser: user.id, action: "data.exported" });
  return new Response(JSON.stringify(data, null, 2), {
    headers: { "Content-Type": "application/json", "Content-Disposition": `attachment; filename="reclaim-data-${new Date().toISOString().slice(0, 10)}.json"`, "Cache-Control": "no-store" },
  });
}
