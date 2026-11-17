import type { Metadata } from "next";
import Link from "next/link";
import { Container, EntityTag } from "@/components/ui";
import { JoinForm } from "./JoinForm";
import { PLANS, ADD_ONS, planPrice } from "@/config/catalog";
import { JURISDICTIONS } from "@/config/site";
import { CONSENTS } from "@/config/consents";
import { activeVariant, activeSubscription } from "@/lib/commerce";
import { currentUser } from "@/lib/auth";
import { track } from "@/lib/analytics";
import { cad } from "@/lib/money";

export const metadata: Metadata = { title: "Join" };

export default async function JoinPage({ searchParams }: { searchParams: Promise<{ plan?: string; path?: string; code?: string; from?: string }> }) {
  const sp = await searchParams;
  const user = await currentUser();
  const path = sp.path === "medical" ? "medical" : "membership";
  const variant = activeVariant();
  await track("join_started", { plan: sp.plan ?? null, variant, source: sp.from ?? null }, user?.id);

  if (user && user.role !== "member") {
    return <Container className="py-16"><p>You&apos;re signed in as staff. Log out to join as a member.</p></Container>;
  }
  const sub = user ? activeSubscription(user.id) : null;
  if (sub && path === "membership") {
    return (
      <Container className="py-16">
        <h1 className="text-4xl">You already have a membership.</h1>
        <p className="mt-3 text-ink-2">Change or cancel it in your portal.</p>
        <Link href="/portal/billing" className="btn-primary mt-6">Go to Billing</Link>
      </Container>
    );
  }

  const plans = PLANS.filter((p) => p.id !== "maintenance").map((p) => ({
    id: p.id, name: p.name, priceCents: planPrice(p, variant), price: cad(planPrice(p, variant)), audience: p.audience, includesBlueprint: p.workload.blueprintMinutesOnce > 0,
  }));
  const addOns = ADD_ONS.map((a) => ({ id: a.id, name: a.name, description: a.description, priceCents: a.priceCents, price: cad(a.priceCents) }));

  return (
    <Container className="py-14">
      <p className="eyebrow">{path === "medical" ? "Medical assessment · free account" : "Join RECLAIM"}</p>
      <h1 className="mt-3 max-w-2xl text-4xl font-medium leading-tight sm:text-5xl">
        {path === "medical" ? "Create a free account to request a medical assessment." : "Choose your programme and create your account."}
      </h1>
      {path === "medical" && (
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-ink-2">
          <EntityTag entity="clinical" />
          No membership needed. After you create an account, the independent practice&apos;s questionnaire opens in your portal.
        </div>
      )}
      <div className="mt-10">
        <JoinForm
          path={path}
          signedIn={!!user}
          defaultPlan={sp.plan ?? "core"}
          defaultCode={sp.code ?? ""}
          plans={plans}
          addOns={addOns}
          provinces={JURISDICTIONS.map(({ code, name, status }) => ({ code, name, live: status === "live" }))}
          consentText={{
            terms: CONSENTS.platform_terms.text,
            privacy: CONSENTS.platform_privacy.text,
            marketing: CONSENTS.marketing_email.text,
            analytics: CONSENTS.product_analytics.text,
            employer: CONSENTS.employer_aggregate.text,
          }}
        />
      </div>
    </Container>
  );
}
