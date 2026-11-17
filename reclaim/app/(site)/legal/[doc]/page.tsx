import { notFound } from "next/navigation";
import Link from "next/link";
import { Container, EntityTag, Notice } from "@/components/ui";
import { LEGAL_DOCS, legalBySlug } from "@/content/legal";
import { ENTITIES } from "@/config/site";

export function generateStaticParams() {
  return LEGAL_DOCS.map((d) => ({ doc: d.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ doc: string }> }) {
  return { title: legalBySlug((await params).doc)?.title ?? "Legal" };
}

export default async function LegalPage({ params }: { params: Promise<{ doc: string }> }) {
  const doc = legalBySlug((await params).doc);
  if (!doc) notFound();
  return (
    <Container className="grid gap-12 py-16 lg:grid-cols-[220px_1fr]">
      <nav aria-label="Legal documents" className="lg:sticky lg:top-24 lg:self-start">
        <p className="eyebrow mb-3">Legal</p>
        <ul className="space-y-1.5 text-sm">
          {LEGAL_DOCS.map((d) => (
            <li key={d.slug}>
              <Link href={`/legal/${d.slug}`} className={d.slug === doc.slug ? "font-semibold text-ink" : "text-ink-2 hover:text-ink"}>{d.title}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <article className="prose-legal max-w-2xl">
        <EntityTag entity={doc.entity} label={`Issued by ${ENTITIES[doc.entity].displayName}`} />
        <h1 className="mt-4 text-4xl font-medium leading-tight">{doc.title}</h1>
        <p className="!mt-3 !text-lg !text-ink-2">{doc.summary}</p>
        <div className="mt-6">
          <Notice tone="warn" title="Draft — not legal advice">
            This page sets out the commitments the website is built to honour. It must be reviewed and replaced by qualified Ontario counsel before launch.
          </Notice>
        </div>
        {doc.sections.map((s) => (
          <section key={s.h}>
            <h2>{s.h}</h2>
            {s.p.map((p) => <p key={p.slice(0, 30)} className="mt-3">{p}</p>)}
          </section>
        ))}
        <section className="mt-12 rounded-2xl border border-line bg-bone/50 p-5">
          <h3 className="!mt-0">Designed around</h3>
          <ul>{doc.basis.map((b) => <li key={b}>{b}</li>)}</ul>
        </section>
      </article>
    </Container>
  );
}
