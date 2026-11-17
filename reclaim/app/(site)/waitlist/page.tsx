import type { Metadata } from "next";
import { Container } from "@/components/ui";
import { WaitlistForm } from "@/components/forms";
import { JURISDICTIONS } from "@/config/site";

export const metadata: Metadata = { title: "Waitlist" };

export default async function WaitlistPage({ searchParams }: { searchParams: Promise<{ j?: string }> }) {
  const { j } = await searchParams;
  const juris = JURISDICTIONS.find((x) => x.code === j);
  return (
    <Container className="py-16">
      <div className="mx-auto max-w-2xl">
        <p className="eyebrow">Waitlist</p>
        <h1 className="mt-4 text-5xl font-medium leading-[1.05]">We&apos;re in Ontario first.</h1>
        <p className="mt-5 text-lg leading-8 text-ink-2">
          Each new province or state needs its own licensed clinicians, pharmacy arrangements and local partners. Waitlist numbers help us decide where to go
          next.
        </p>
        {juris?.note && <p className="mt-3 text-sm text-muted">{juris.note}</p>}
        <div className="card mt-8 p-6"><WaitlistForm defaultJurisdiction={juris && juris.status !== "live" ? juris.code : ""} /></div>
      </div>
    </Container>
  );
}
