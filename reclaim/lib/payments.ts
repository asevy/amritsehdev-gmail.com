import "server-only";

/**
 * Payment provider seam.
 *
 * Production design (not implemented here — no keys in this prototype):
 *  - Stripe (or equivalent) with ONE ACCOUNT PER LEGAL ENTITY (e.g. Stripe Connect
 *    standard accounts or separate accounts), so funds for memberships, uninsured
 *    clinical fees and medication settle directly to the entity that supplies them.
 *    The platform never collects medication money and takes no per-prescription or
 *    percentage application fee from the practice or pharmacy.
 *  - Hosted Checkout in subscription mode for memberships; a webhook (signature-
 *    verified) calls completeOrder(). Card data never touches our servers.
 *  - Customer portal is NOT used for cancellation: cancellation stays in our own
 *    two-click Billing screen so it always matches the agreement we disclosed.
 */
export interface PaymentProvider {
  name: string;
  createCheckout(input: { orderId: string; amountCents: number; customerEmail: string; description: string }): Promise<{ redirectUrl: string }>;
}

const mockProvider: PaymentProvider = {
  name: "mock",
  async createCheckout({ orderId }) {
    return { redirectUrl: `/checkout/${orderId}` };
  },
};

export function getPaymentProvider(): PaymentProvider {
  if (process.env.STRIPE_SECRET_KEY) {
    // Intentionally not implemented in the prototype: wire Stripe here and verify webhooks in app/api/payments/webhook.
    throw new Error("STRIPE_SECRET_KEY is set but the Stripe adapter is not implemented in this prototype. Unset it to use the mock provider.");
  }
  return mockProvider;
}
