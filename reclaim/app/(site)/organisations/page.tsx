import type { Metadata } from "next";
import { Container, Notice } from "@/components/ui";
import { LeadForm } from "@/components/forms";

export const metadata: Metadata = { title: "Clinics & gyms — licensing" };

export default function OrganisationsPage() {
  return (
    <>
      <Container className="py-16">
        <p className="eyebrow">For clinics, gyms and allied-health groups</p>
        <h1 className="mt-4 max-w-3xl text-5xl font-medium leading-[1.05]">License the Blueprint method and software.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">
          Run the RECLAIM assessment-to-action method in your own setting: the assessment and Blueprint tools, the coaching curriculum and form-check review workflow,
          and outcome reporting on your own clients.
        </p>
      </Container>
      <Container className="grid gap-5 md:grid-cols-3">
        {[
          ["Software licence", "Per-seat licence for the assessment, Blueprint builder, plan library and outcome dashboards. Your client data stays yours."],
          ["Method & curriculum", "Coach training, lesson and video curriculum, and quality standards — licensed, not sold outright."],
          ["Implementation", "Fixed-fee onboarding priced separately from the licence, so ongoing fees don't depend on delivering care."],
        ].map(([h, p]) => (
          <div key={h} className="card p-6"><h2 className="text-2xl">{h}</h2><p className="mt-2 text-[15px] leading-7 text-ink-2">{p}</p></div>
        ))}
      </Container>
      <Container className="grid gap-10 py-16 lg:grid-cols-2">
        <Notice tone="warn" title="Early access">
          Licensing becomes available once the method has outcome data from our own pilot. Register interest now; we don&apos;t sell software that makes
          clinical recommendations without the necessary regulatory review.
        </Notice>
        <div className="card p-6"><LeadForm kind="enterprise" messageLabel="Your setting and what you'd use it for" /></div>
      </Container>
    </>
  );
}
