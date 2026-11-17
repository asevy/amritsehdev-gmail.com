import { FORM_EXERCISES, RATING_LABEL } from "@/config/exercises";
import { METRICS } from "@/lib/mechanics";
import { clipUrl, formScore, nextDue, type FormCheck } from "@/lib/form-checks";
import { fmtDate } from "@/lib/money";

const RATING_STYLE: Record<number, string> = {
  1: "bg-ember-soft text-ember",
  2: "bg-warn-soft text-warn",
  3: "bg-moss-soft text-moss",
};

/** One exercise's history: first vs latest side by side, then every check in a progress table. */
export function FormHistory({
  checks, exerciseId, viewerId, deleteAction, compact = false,
}: {
  checks: FormCheck[];
  exerciseId: string;
  viewerId: string;
  deleteAction?: (form: FormData) => Promise<void>;
  compact?: boolean;
}) {
  const ex = FORM_EXERCISES.find((e) => e.id === exerciseId)!;
  const list = checks.filter((c) => c.exercise === exerciseId);
  if (list.length === 0) return null;
  const withVideo = list.filter((c) => c.file_path);
  const first = withVideo[0], latest = withVideo.at(-1);
  const scored = list.filter((c) => c.scores);
  const firstScore = scored[0] ? formScore(scored[0]) : null, lastScore = scored.at(-1) ? formScore(scored.at(-1)!) : null;
  const due = nextDue(checks, ex.id);
  const lastCues = [...list].reverse().find((c) => c.cues);

  return (
    <section id={ex.id} className="card scroll-mt-6 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-sans text-lg font-semibold tracking-normal">{ex.name}</h2>
        <p className="text-sm text-ink-2">
          {list.length} check{list.length === 1 ? "" : "s"}
          {firstScore != null && lastScore != null && scored.length > 1 && <> · form score {firstScore}% → <strong>{lastScore}%</strong></>}
          {due && <> · re-film {due.getTime() <= Date.now() ? <strong className="text-ember">due now</strong> : `due ${fmtDate(due.toISOString())}`}</>}
        </p>
      </div>

      {!compact && first && latest && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {(first.id !== latest.id ? [first, latest] : [latest]).map((c, i) => (
            <figure key={c.id}>
              <video src={clipUrl(viewerId, c)!} controls muted playsInline preload="metadata" className="aspect-video w-full rounded-xl bg-ink object-contain" aria-label={`${ex.name}, ${fmtDate(c.created_at)}`} />
              <figcaption className="mt-1 text-xs text-muted">{first.id !== latest.id ? (i === 0 ? "First" : "Latest") : "Latest"} · {fmtDate(c.created_at)} · recorded by {c.recorded_by === "coach" ? "your coach" : "you"}</figcaption>
            </figure>
          ))}
        </div>
      )}

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <caption className="sr-only">{ex.name} form checks over time</caption>
          <thead>
            <tr className="text-left text-xs text-muted">
              <th className="py-1.5 pr-3 font-medium">Check</th>
              {list.map((c) => <th key={c.id} className="py-1.5 pr-3 font-medium">{fmtDate(c.created_at, { month: "short", day: "numeric" })}{c.recorded_by === "coach" ? " · coach" : ""}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {ex.criteria.map((cr) => (
              <tr key={cr.id}>
                <th scope="row" className="py-1.5 pr-3 text-left font-normal text-ink-2">{cr.label}</th>
                {list.map((c) => {
                  const v = c.scores?.[cr.id];
                  return <td key={c.id} className="py-1.5 pr-3">{v ? <span className={`rounded-md px-1.5 py-0.5 text-xs font-medium ${RATING_STYLE[v]}`}>{RATING_LABEL[v]}</span> : <span className="text-xs text-muted">{c.status === "submitted" ? "awaiting coach" : "—"}</span>}</td>;
                })}
              </tr>
            ))}
            <tr>
              <th scope="row" className="py-1.5 pr-3 text-left font-medium">Form score</th>
              {list.map((c) => <td key={c.id} className="py-1.5 pr-3 font-semibold tabular-nums">{formScore(c) != null ? `${formScore(c)}%` : "—"}</td>)}
            </tr>
            {METRICS[ex.id].map((m) => (
              <tr key={m.key}>
                <th scope="row" className="py-1.5 pr-3 text-left font-normal text-ink-2">{m.label} <span className="text-xs text-muted">(est.)</span></th>
                {list.map((c) => {
                  const v = c.mechanics?.metrics[m.key];
                  return <td key={c.id} className="py-1.5 pr-3 tabular-nums">{v != null ? `${v}${m.unit}` : <span className="text-xs text-muted">—</span>}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
        {list.some((c) => c.mechanics?.demo) && <p className="mt-1 text-xs text-muted">Demo account: measurements shown are illustrative values, not from a real person.</p>}
      </div>

      {lastCues && (
        <div className="mt-4 rounded-xl border border-moss/25 bg-moss-soft/50 p-3 text-sm">
          <p className="text-xs font-medium text-moss">Coach cues · {fmtDate(lastCues.reviewed_at)}</p>
          <p className="mt-1 text-ink">{lastCues.cues}</p>
        </div>
      )}

      {deleteAction && !compact && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-xs text-muted">Manage these videos</summary>
          <ul className="mt-2 space-y-2">
            {list.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line p-2">
                <span>{fmtDate(c.created_at)} · {c.file_path ? "video stored" : "no video stored"}{c.member_note ? ` · “${c.member_note}”` : ""}</span>
                <span className="flex gap-2">
                  {c.file_path && <form action={deleteAction}><input type="hidden" name="id" value={c.id} /><input type="hidden" name="mode" value="video" /><button className="btn-ghost btn-sm">Delete video, keep results</button></form>}
                  <form action={deleteAction}><input type="hidden" name="id" value={c.id} /><input type="hidden" name="mode" value="all" /><button className="btn-danger btn-sm">Remove entirely</button></form>
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
