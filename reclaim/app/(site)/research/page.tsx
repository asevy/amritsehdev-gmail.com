import type { Metadata } from "next";
import { Container, SectionHeading, Notice } from "@/components/ui";
import { LeadForm } from "@/components/forms";

export const metadata: Metadata = { title: "Research" };

export default function ResearchPage() {
  return (
    <>
      <Container className="py-16">
        <p className="eyebrow">Research</p>
        <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05]">Research with consent, ethics review and published methods.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
          We separate routine quality improvement (checking our own service works) from research (generating knowledge for others). Research only happens
          with research-ethics-board approval and your separate, optional consent.
        </p>
      </Container>
      <Container className="grid gap-5 md:grid-cols-2">
        {[
          ["We never sell personal information", "Not to researchers, insurers, employers, advertisers or anyone else. Research partners receive de-identified data under a written agreement, or none at all."],
          ["Opt in, opt out", "Research use is off by default. You can turn it on or off at any time in Privacy settings; it never affects your care or price."],
          ["Ethics first", "Every study is reviewed by an independent research ethics board before it starts, and registered publicly where appropriate."],
          ["Results published", "We publish methods and results — including null or negative results — on our Outcomes page."],
        ].map(([h, p]) => (
          <div key={h} className="card p-6"><h2 className="text-2xl">{h}</h2><p className="mt-2 text-[15px] leading-7 text-ink-2">{p}</p></div>
        ))}
      </Container>
      <Container className="grid gap-10 py-16 lg:grid-cols-2">
        <div className="space-y-4">
          <SectionHeading eyebrow="Current studies" title="None recruiting yet." />
          <Notice>We&apos;ll list studies here, with the ethics approval number and lead investigator, when they open.</Notice>
        </div>
        <div className="card p-6">
          <p className="mb-4 font-semibold">Academic or industry research partners</p>
          <LeadForm kind="research" messageLabel="Your research question and institution" />
        </div>
      </Container>
    </>
  );
}
