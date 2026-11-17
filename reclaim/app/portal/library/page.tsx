import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { VIDEOS, CATEGORY_LABEL, type VideoCategory } from "@/lib/videos";
import { progressFor, memberPlayback } from "@/lib/media-auth";
import { toggleSaveVideo } from "@/app/actions/portal";
import { PageHeader, MembershipRequired } from "@/components/portal";

export default async function LibraryPage({ searchParams }: { searchParams: Promise<{ filter?: string }> }) {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const { filter } = await searchParams;
  const prog = progressFor(user.id);
  const filters = [["all", "All"], ["saved", "Saved"], ["continue", "Continue"], ["movement", "Movement"], ["lesson", "Lessons"], ["assessment", "Assessments"], ["programme", "Programme"]];
  const list = VIDEOS.filter((v) => {
    const p = prog.get(v.id);
    if (filter === "saved") return p?.saved === 1;
    if (filter === "continue") return p && !p.completed_at && p.position_s > 2;
    if (filter && filter !== "all") return v.category === filter;
    return true;
  });
  return (
    <>
      <PageHeader eyebrow="Video library" title="Watch, learn, practise">Every video has captions, chapters and a transcript. Your place is saved automatically.</PageHeader>
      <nav aria-label="Filter videos" className="mb-6 flex flex-wrap gap-2">
        {filters.map(([k, l]) => (
          <Link key={k} href={k === "all" ? "/portal/library" : `/portal/library?filter=${k}`} className={`rounded-full border px-3 py-1 text-sm ${(filter ?? "all") === k ? "border-ink bg-ink text-paper" : "border-line-2 bg-card hover:bg-bone"}`}>{l}</Link>
        ))}
      </nav>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((v) => {
          const p = prog.get(v.id);
          const pct = p?.completed_at ? 1 : p && p.duration_s ? p.position_s / p.duration_s : 0;
          const poster = v.access === "public" ? `/media/public/${v.id}/poster.jpg` : memberPlayback(v, user.id).poster;
          return (
            <div key={v.id} className="card overflow-hidden">
              <Link href={`/portal/library/${v.id}`} className="group block">
                <div className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={poster} alt="" className="aspect-video w-full object-cover" />
                  <div className="absolute inset-x-0 bottom-0 h-1 bg-ink/40"><div className="h-1 bg-lime" style={{ width: `${pct * 100}%` }} /></div>
                  {p?.completed_at && <span className="chip absolute right-2 top-2 border-transparent bg-lime text-ink">Done</span>}
                </div>
                <div className="p-4">
                  <p className="eyebrow">{CATEGORY_LABEL[v.category as VideoCategory]} · {Math.round(v.durationS)} s</p>
                  <p className="mt-1 font-semibold group-hover:underline">{v.title}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-2">{v.summary}</p>
                </div>
              </Link>
              <form action={toggleSaveVideo} className="px-4 pb-4">
                <input type="hidden" name="videoId" value={v.id} />
                <button className="text-sm text-muted underline hover:text-ink">{p?.saved ? "★ Saved — remove" : "☆ Save to my library"}</button>
              </form>
            </div>
          );
        })}
      </div>
      {list.length === 0 && <p className="text-muted">Nothing here yet.</p>}
    </>
  );
}
