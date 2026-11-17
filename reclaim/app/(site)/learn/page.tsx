import type { Metadata } from "next";
import Link from "next/link";
import { Container, DraftBadge } from "@/components/ui";
import { ARTICLES } from "@/content/articles";
import { VIDEOS } from "@/lib/videos";

export const metadata: Metadata = { title: "Learn" };

export default function LearnPage() {
  const publicVideos = VIDEOS.filter((v) => v.access === "public");
  return (
    <Container className="py-16">
      <p className="eyebrow">Learn</p>
      <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05]">Evidence, explained plainly.</h1>
      <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
        General health information with references and a named clinical reviewer. It isn&apos;t medical advice and doesn&apos;t discuss specific prescription
        products — for that, talk to a clinician.
      </p>
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {ARTICLES.map((a) => (
          <Link key={a.slug} href={`/learn/${a.slug}`} className="card group flex flex-col p-6 hover:border-line-2">
            <div className="flex items-center justify-between">
              <span className="eyebrow">{a.readMinutes} min read</span>
              {a.status === "draft" && <DraftBadge>Pending clinical review</DraftBadge>}
            </div>
            <h2 className="mt-4 text-2xl leading-tight group-hover:underline">{a.title}</h2>
            <p className="mt-3 flex-1 text-sm leading-6 text-ink-2">{a.summary}</p>
            <p className="mt-4 font-mono text-[11px] text-muted">{a.references.length} references</p>
          </Link>
        ))}
      </div>
      <h2 className="mt-16 text-3xl">Videos</h2>
      <div className="mt-6 grid gap-5 md:grid-cols-2">
        {publicVideos.map((v) => (
          <Link key={v.id} href={`/learn/video/${v.id}`} className="card group overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`/media/public/${v.id}/poster.jpg`} alt="" className="aspect-video w-full object-cover" />
            <div className="p-5">
              <p className="font-semibold group-hover:underline">{v.title}</p>
              <p className="mt-1 text-sm text-ink-2">{v.summary}</p>
              <p className="mt-2 font-mono text-[11px] text-muted">{Math.round(v.durationS)} s · captions · transcript</p>
            </div>
          </Link>
        ))}
      </div>
      <p className="mt-10 text-sm text-muted">Members get the full movement library and lesson curriculum in their portal.</p>
    </Container>
  );
}
