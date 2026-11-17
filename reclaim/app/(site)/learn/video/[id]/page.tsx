import { notFound } from "next/navigation";
import Link from "next/link";
import { Container } from "@/components/ui";
import { VideoPlayer } from "@/components/VideoPlayer";
import { VIDEOS, videoById, publicPlayback } from "@/lib/videos";

export function generateStaticParams() {
  return VIDEOS.filter((v) => v.access === "public").map((v) => ({ id: v.id }));
}

export default async function PublicVideoPage({ params }: { params: Promise<{ id: string }> }) {
  const v = videoById((await params).id);
  if (!v || v.access !== "public") notFound();
  return (
    <Container className="py-14">
      <div className="mx-auto max-w-4xl">
        <Link href="/learn" className="text-sm text-muted hover:text-ink">← Learn</Link>
        <h1 className="mt-4 text-4xl font-medium">{v.title}</h1>
        <p className="mt-2 text-ink-2">{v.summary}</p>
        <div className="mt-8">
          <VideoPlayer videoId={v.id} title={v.title} playback={publicPlayback(v)} chapters={v.chapters} cues={v.cues} />
        </div>
      </div>
    </Container>
  );
}
