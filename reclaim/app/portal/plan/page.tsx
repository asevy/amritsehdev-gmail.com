import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { currentWeekItems, DAY_NAMES } from "@/lib/portal-data";
import { togglePlanItem } from "@/app/actions/portal";
import { videoById } from "@/lib/videos";
import { PageHeader, MembershipRequired } from "@/components/portal";

const KIND_STYLE: Record<string, string> = {
  training: "bg-moss-soft text-moss", habit: "bg-bone text-ink-2", lesson: "bg-lime/40 text-ink", nutrition: "bg-ember-soft text-ember", test: "bg-clinic-soft text-clinic",
};

export default async function PlanPage() {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const items = currentWeekItems(user.id);
  const done = items.filter((i) => i.done_at).length;
  return (
    <>
      <PageHeader eyebrow={items[0] ? `Week of ${items[0].week_start}` : "This week"} title="This week">
        {done} of {items.length} done. Your coach reviews the week before your next plan update.
      </PageHeader>
      {items.length === 0 && <p className="text-muted">Your coach will publish your first week after your Blueprint session.</p>}
      <ol className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {DAY_NAMES.map((d, day) => (
          <li key={d} className="card p-4">
            <p className="eyebrow">{d}</p>
            <ul className="mt-3 space-y-3">
              {items.filter((i) => i.day === day).map((i) => (
                <li key={i.id} className="flex gap-3">
                  <form action={togglePlanItem}>
                    <input type="hidden" name="id" value={i.id} />
                    <button aria-label={i.done_at ? `Mark ${i.title} not done` : `Mark ${i.title} done`} className={`grid size-6 place-items-center rounded-md border text-sm ${i.done_at ? "border-series bg-series text-white" : "border-line-2 hover:border-ink"}`}>{i.done_at ? "✓" : ""}</button>
                  </form>
                  <div className="min-w-0">
                    <span className={`chip border-transparent ${KIND_STYLE[i.kind]}`}>{i.kind}</span>
                    <p className={`mt-1 text-sm font-medium ${i.done_at ? "text-muted line-through" : ""}`}>{i.title}</p>
                    {i.detail && <p className="text-xs leading-5 text-ink-2">{i.detail}</p>}
                    {i.video_id && <Link className="text-xs underline" href={`/portal/library/${i.video_id}`}>{videoById(i.video_id)?.title}</Link>}
                  </div>
                </li>
              ))}
              {items.filter((i) => i.day === day).length === 0 && <li className="text-sm text-muted">Rest</li>}
            </ul>
          </li>
        ))}
      </ol>
    </>
  );
}
