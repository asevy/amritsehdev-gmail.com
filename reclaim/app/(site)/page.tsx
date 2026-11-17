import Link from "next/link";
import { Container, SectionHeading, ArrowLink, EntityTag, HypothesisBadge } from "@/components/ui";
import { BlueprintCard } from "@/components/BlueprintCard";
import { VideoPlayer } from "@/components/VideoPlayer";
import { PLANS, planPrice } from "@/config/catalog";
import { VIDEOS, publicPlayback } from "@/lib/videos";
import { activeVariant } from "@/lib/commerce";
import { cad } from "@/lib/money";

export default function Home() {
  const video = VIDEOS.find((v) => v.id === "how-it-works")!;
  const variant = activeVariant();
  const featured = PLANS.filter((p) => ["foundation", "core", "hybrid"].includes(p.id));

  return (
    <>
      {/* Hero */}
      <section className="border-b border-line">
        <Container className="grid items-center gap-14 py-16 lg:grid-cols-[1.1fr_0.9fr] lg:py-24">
          <div>
            <p className="eyebrow">Ontario · founding members now enrolling</p>
            <h1 className="mt-5 text-[44px] font-medium leading-[1.02] sm:text-6xl lg:text-[68px]">
              Get stronger. <br className="hidden sm:block" />
              Change your body composition. <span className="italic text-moss">Measure it.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-ink-2">
              RECLAIM is a coached programme built on your personal Blueprint — training, nutrition, sleep and habits that fit your real week — with
              clinician-led care from an independent medical practice when it&apos;s appropriate for you.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/assessment" className="btn-primary">
                Take the free assessment · 4 min
              </Link>
              <Link href="/programmes" className="btn-ghost">
                See programmes
              </Link>
            </div>
            <p className="mt-4 text-sm text-muted">We don&apos;t ask for your weight or medical history here. Your answers stay on your device until you join.</p>
          </div>
          <BlueprintCard />
        </Container>
      </section>

      {/* Who does what */}
      <section className="border-b border-line bg-bone/50">
        <Container className="py-14">
          <p className="eyebrow">Who does what</p>
          <div className="mt-6 grid gap-5 md:grid-cols-3">
            {[
              {
                e: "platform" as const,
                h: "RECLAIM",
                p: "Your assessment, Blueprint, coaching, video library, progress tracking and the local partner network. We do not practise medicine or dispense medication.",
              },
              {
                e: "clinical" as const,
                h: "An independent medical practice",
                p: "If you ask for it, physicians and nurse practitioners assess you and decide — on their own clinical judgement — whether any test or treatment is appropriate. OHIP-insured care is never charged to you.",
              },
              {
                e: "pharmacy" as const,
                h: "The pharmacy you choose",
                p: "If something is prescribed, you choose where to fill it: our partner pharmacy with home delivery, any other pharmacy, or a copy to take yourself.",
              },
            ].map((c) => (
              <div key={c.h} className="card p-6">
                <EntityTag entity={c.e} />
                <h3 className="mt-4 text-2xl">{c.h}</h3>
                <p className="mt-2 text-[15px] leading-7 text-ink-2">{c.p}</p>
              </div>
            ))}
          </div>
          <div className="mt-5">
            <ArrowLink href="/about#structure">How the structure protects clinical independence</ArrowLink>
          </div>
        </Container>
      </section>

      {/* How it works + video */}
      <section>
        <Container className="grid gap-12 py-20 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <SectionHeading eyebrow="How it works" title="Assessment to action, then measured.">
              Five steps, repeated every few weeks. Every step is something you can see in your portal.
            </SectionHeading>
            <ol className="mt-8 space-y-5">
              {[
                ["Assess", "Goals, schedule, how you move today, pain, sleep and what has got in the way before."],
                ["Blueprint", "A written plan with three measurable targets, built with a coach in a 60-minute session."],
                ["Train, eat, recover", "Weekly sessions at home, in a partner gym or with a trainer, plus nutrition and sleep habits."],
                ["Clinician review — if appropriate", "Request an assessment by the independent practice. The clinician decides; nothing is automatic."],
                ["Measure and adjust", "Strength tests, waist, body composition and adherence, re-checked on a schedule."],
              ].map(([h, p], i) => (
                <li key={h} className="flex gap-4">
                  <span className="mt-0.5 font-mono text-sm text-ember">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <p className="font-semibold">{h}</p>
                    <p className="text-[15px] leading-7 text-ink-2">{p}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <div>
            <VideoPlayer title={video.title} playback={publicPlayback(video)} chapters={video.chapters} cues={video.cues} />
          </div>
        </Container>
      </section>

      {/* Why */}
      <section className="bg-ink text-paper">
        <Container className="py-20">
          <p className="eyebrow !text-paper/50">Why a programme, not a single product</p>
          <h2 className="mt-3 max-w-3xl text-4xl font-medium leading-tight sm:text-5xl">
            Body composition is about what you keep, not just what you lose.
          </h2>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            {[
              {
                h: "More than a prescription",
                p: "When people eat less, part of the weight lost can be lean tissue. Resistance training and adequate protein help preserve it. Every RECLAIM plan is built around strength.",
                ref: "Weinheimer et al., Nutr Rev 2010",
              },
              {
                h: "More than a workout plan",
                p: "Coaching is adapted to pain, schedule, sleep and the barriers you name — and if you want it, an independent clinician can review whether medical care is appropriate.",
              },
              {
                h: "More than a gym membership",
                p: "Partner gyms, studios and trainers run the sessions your coach programmes, and the results flow back into one record of your progress.",
              },
            ].map((c) => (
              <div key={c.h} className="border-t border-paper/20 pt-6">
                <h3 className="text-2xl text-paper">{c.h}</h3>
                <p className="mt-3 text-[15px] leading-7 text-paper/75">{c.p}</p>
                {c.ref && <p className="mt-3 font-mono text-[11px] text-paper/45">Evidence: {c.ref} · see Learn</p>}
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* Programmes preview */}
      <section>
        <Container className="py-20">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <SectionHeading eyebrow="Programmes" title="Pay for the support you'll actually use.">
              Monthly, cancel online any time. Medical care and medication are never bundled into a membership price.
            </SectionHeading>
            <ArrowLink href="/programmes">Compare all five programmes</ArrowLink>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {featured.map((p) => (
              <div key={p.id} className={`card flex flex-col p-6 ${p.highlight ? "ring-2 ring-ink" : ""}`}>
                <div className="flex items-center justify-between">
                  <h3 className="text-2xl">{p.name}</h3>
                  <HypothesisBadge />
                </div>
                <p className="mt-3 font-mono text-3xl tabular-nums">
                  {cad(planPrice(p, variant))}
                  <span className="text-sm text-muted"> /month + HST</span>
                </p>
                <p className="mt-3 text-sm leading-6 text-ink-2">{p.audience}</p>
                <ul className="mt-4 flex-1 space-y-2 text-sm">
                  {p.includes.slice(0, 3).map((i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-moss">✓</span>
                      {i}
                    </li>
                  ))}
                </ul>
                <Link href={`/join?plan=${p.id}`} className={`mt-6 ${p.highlight ? "btn-primary" : "btn-ghost"}`}>
                  Choose {p.name}
                </Link>
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* Measured */}
      <section className="border-y border-line bg-bone/50">
        <Container className="grid gap-12 py-20 lg:grid-cols-2">
          <SectionHeading eyebrow="Measured" title="We'll publish our methods before our results.">
            Outcomes are measured the same way for every member and reported in aggregate — including what didn&apos;t work. No testimonials, no before-and-after
            photos.
          </SectionHeading>
          <div className="grid grid-cols-2 gap-4">
            {[
              ["Strength & form", "30-s sit-to-stand, push-up progression, and form checks your coach rates over time"],
              ["Body composition", "Waist; partner-facility scans where you choose"],
              ["Habits", "Sessions completed, protein, sleep, steps"],
              ["Safety", "Pain flags and side-effect reports, reviewed by the right professional"],
            ].map(([h, p]) => (
              <div key={h} className="card p-5">
                <p className="font-semibold">{h}</p>
                <p className="mt-1 text-sm leading-6 text-ink-2">{p}</p>
              </div>
            ))}
            <div className="col-span-2">
              <ArrowLink href="/outcomes">Read the outcomes protocol</ArrowLink>
            </div>
          </div>
        </Container>
      </section>

      {/* Employers + final */}
      <section>
        <Container className="grid gap-6 py-20 md:grid-cols-2">
          <div className="card p-8">
            <p className="eyebrow">For employers</p>
            <h3 className="mt-3 text-3xl">Sponsor RECLAIM for your team.</h3>
            <p className="mt-3 text-[15px] leading-7 text-ink-2">
              You see aggregate participation and outcomes for groups of 10 or more — never an individual&apos;s data.
            </p>
            <div className="mt-6">
              <ArrowLink href="/employers">Employer programmes</ArrowLink>
            </div>
          </div>
          <div className="rounded-2xl bg-lime p-8">
            <p className="eyebrow !text-ink/60">Start here</p>
            <h3 className="mt-3 text-3xl">Four minutes. No weight, no medical history.</h3>
            <p className="mt-3 text-[15px] leading-7 text-ink/80">Get a suggested programme with the reasons behind it, then decide.</p>
            <Link href="/assessment" className="btn-primary mt-6">
              Take the free assessment
            </Link>
          </div>
        </Container>
      </section>
    </>
  );
}
