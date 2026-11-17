/**
 * Sales-tax configuration.
 *
 * Status: ASSUMPTION — confirm every rate and every product's tax code with an
 * accountant before launch. Only Ontario is live in this build. Rates outside
 * Ontario are included so waitlisted provinces can be switched on later; the
 * treatment of services under provincial PST/RST/QST in particular needs review.
 *
 * Tax codes are attached to every catalogue item (see config/catalog.ts) so the
 * checkout never guesses. Supplies by the medical practice and the pharmacy are
 * NOT taxed by the platform: those entities are merchant of record for their own
 * supplies and apply their own treatment.
 */

export type TaxCode =
  | "taxable_service" // coaching, programme design, digital access — GST/HST applies
  | "taxable_goods" // devices, printed materials
  | "exempt_health_service" // physician / NP services (exempt) — charged by the medical practice only
  | "zero_rated_rx"; // prescription drugs and their dispensing — charged by the pharmacy only

export interface TaxRate {
  label: string;
  /** Combined rate applied to taxable services, in basis points (1300 = 13%). */
  servicesBps: number;
  /** Combined rate applied to taxable goods. */
  goodsBps: number;
  status: "assumption";
}

export const TAX_RATES: Record<string, TaxRate> = {
  ON: { label: "HST 13%", servicesBps: 1300, goodsBps: 1300, status: "assumption" },
  NS: { label: "HST 14%", servicesBps: 1400, goodsBps: 1400, status: "assumption" },
  NB: { label: "HST 15%", servicesBps: 1500, goodsBps: 1500, status: "assumption" },
  NL: { label: "HST 15%", servicesBps: 1500, goodsBps: 1500, status: "assumption" },
  PE: { label: "HST 15%", servicesBps: 1500, goodsBps: 1500, status: "assumption" },
  AB: { label: "GST 5%", servicesBps: 500, goodsBps: 500, status: "assumption" },
  BC: { label: "GST 5% (+PST on goods)", servicesBps: 500, goodsBps: 1200, status: "assumption" },
  SK: { label: "GST 5% (+PST — services to confirm)", servicesBps: 500, goodsBps: 1100, status: "assumption" },
  MB: { label: "GST 5% (+RST — services to confirm)", servicesBps: 500, goodsBps: 1200, status: "assumption" },
  QC: { label: "GST 5% + QST 9.975%", servicesBps: 1497, goodsBps: 1497, status: "assumption" },
};

export function taxFor(code: TaxCode, province: string, amountCents: number): { cents: number; label: string } {
  const rate = TAX_RATES[province];
  if (!rate) return { cents: 0, label: "Tax: province not configured" };
  if (code === "taxable_service") return { cents: Math.round((amountCents * rate.servicesBps) / 10000), label: rate.label };
  if (code === "taxable_goods") return { cents: Math.round((amountCents * rate.goodsBps) / 10000), label: rate.label };
  if (code === "exempt_health_service") return { cents: 0, label: "Exempt health service" };
  return { cents: 0, label: "Zero-rated prescription" };
}
