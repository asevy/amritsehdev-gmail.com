import type { Metadata } from "next";
import { Container } from "@/components/ui";
import { Assessment } from "./Assessment";
import { PLANS, planPrice } from "@/config/catalog";
import { JURISDICTIONS, LIVE_CODES } from "@/config/site";
import { activeVariant } from "@/lib/commerce";
import { cad } from "@/lib/money";

export const metadata: Metadata = { title: "Free assessment" };

export default function AssessmentPage() {
  const variant = activeVariant();
  const plans = PLANS.filter((p) => p.id !== "maintenance").map((p) => ({ id: p.id, name: p.name, price: cad(planPrice(p, variant)), includes: p.includes }));
  return (
    <Container className="py-14 lg:py-20">
      <Assessment plans={plans} liveCodes={LIVE_CODES} jurisdictions={JURISDICTIONS.map(({ code, name, status }) => ({ code, name, status }))} />
    </Container>
  );
}
