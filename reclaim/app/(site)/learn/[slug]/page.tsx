import { notFound } from "next/navigation";
import Link from "next/link";
import { Container, Notice } from "@/components/ui";
import { ARTICLES, articleBySlug } from "@/content/articles";

export function generateStaticParams() {
  return ARTICLES.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const a = articleBySlug((await params).slug);
  return { title: a?.title ?? "Learn" };
}

export default async function ArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const a = articleBySlug((await params).slug);
  if (!a) notFound();
  return (
    <Container className="py-16">
      <article className="mx-auto max-w-2xl">
        <Link href="/learn" className="text-sm text-muted hover:text-ink">← Learn</Link>
        <h1 className="mt-6 text-5xl font-medium leading-[1.05]">{a.title}</h1>
        <p className="mt-4 text-lg leading-8 text-ink-2">{a.summary}</p>
        <div className="mt-6 flex flex-wrap gap-x-6 gap-y-1 border-y border-line py-3 font-mono text-xs text-muted">
          <span>Clinical reviewer: {a.reviewer ?? "pending"}</span>
          <span>Last reviewed: {a.reviewedAt ?? "—"}</span>
          <span>{a.references.length} references</span>
        </div>
        {a.status === "draft" && (
          <div className="mt-6">
            <Notice tone="warn" title="Draft — not yet clinically reviewed">This article must be reviewed and signed off by the medical director before publication.</Notice>
          </div>
        )}
        {a.sections.map((s) => (
          <section key={s.heading} className="mt-10">
            <h2 className="text-2xl">{s.heading}</h2>
            {s.body.map((p) => (
              <p key={p.slice(0, 24)} className="mt-4 text-[17px] leading-8 text-ink-2">{p}</p>
            ))}
          </section>
        ))}
        <section className="mt-12 rounded-2xl border border-line bg-bone/50 p-6">
          <h2 className="font-sans text-sm font-semibold uppercase tracking-wider text-muted">References</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-ink-2">
            {a.references.map((r) => <li key={r}>{r}</li>)}
          </ol>
        </section>
        <p className="mt-8 text-sm text-muted">General information only, not medical advice. If you have a health condition, talk to your clinician.</p>
      </article>
    </Container>
  );
}
