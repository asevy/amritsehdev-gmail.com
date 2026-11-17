import Link from "next/link";
import { notFound } from "next/navigation";
import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { videoById, publicPlayback, CATEGORY_LABEL } from "@/lib/videos";
import { memberPlayback, progressFor } from "@/lib/media-auth";
import { toggleSaveVideo } from "@/app/actions/portal";
import { VideoPlayer } from "@/components/VideoPlayer";
import { MembershipRequired } from "@/components/portal";

export default async function VideoPage({ params }: { params: Promise<{ id: string }> }) {
  const user = await requireUser(["member"]);
  if (!activeSubscription(user.id)) return <MembershipRequired />;
  const v = videoById((await params).id);
  if (!v) notFound();
  const p = progressFor(user.id).get(v.id);
  const playback = v.access === "public" ? publicPlayback(v) : memberPlayback(v, user.id);
  return (
    <div className="max-w-4xl">
      <Link href="/portal/library" className="text-sm text-muted hover:text-ink">← Library</Link>
      <p className="eyebrow mt-6">{CATEGORY_LABEL[v.category]} · {v.access === "member" ? "members" : "public"}</p>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
        <h1 className="text-4xl font-medium">{v.title}</h1>
        <form action={toggleSaveVideo}>
          <input type="hidden" name="videoId" value={v.id} />
          <button className="btn-ghost btn-sm">{p?.saved ? "★ Saved" : "☆ Save"}</button>
        </form>
      </div>
      <p className="mt-2 text-ink-2">{v.summary}</p>
      <div className="mt-6">
        <VideoPlayer videoId={v.id} title={v.title} playback={playback} chapters={v.chapters} cues={v.cues} startAt={p?.completed_at ? 0 : p?.position_s ?? 0} trackProgress />
      </div>
      <p className="mt-6 text-xs text-muted">Stop if anything causes sharp pain, dizziness or chest discomfort. Placeholder video — produced content will replace it.</p>
    </div>
  );
}
