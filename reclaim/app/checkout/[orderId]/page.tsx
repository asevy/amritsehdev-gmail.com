import { notFound } from "next/navigation";
import { requireUser } from "@/lib/auth";
import { getOrder } from "@/lib/commerce";
import { payMock } from "@/app/actions/commerce";
import { cadExact } from "@/lib/money";
import { ENTITIES } from "@/config/site";

/**
 * MOCK hosted payment page. In production this is the payment provider's own page
 * (e.g. Stripe Checkout) on its domain; it exists here so the full flow can be demonstrated.
 */
export default async function MockCheckout({ params, searchParams }: { params: Promise<{ orderId: string }>; searchParams: Promise<{ declined?: string }> }) {
  const user = await requireUser(["member"]);
  const { orderId } = await params;
  const { declined } = await searchParams;
  const order = getOrder(orderId, user.id);
  if (!order) notFound();
  return (
    <main id="main" className="min-h-screen bg-[#f3f4f6] py-12 font-sans">
      <div className="mx-auto max-w-md">
        <div className="rounded-xl border-2 border-dashed border-amber-500 bg-amber-50 px-4 py-2 text-center text-xs font-semibold text-amber-800">
          TEST MODE — simulated payment provider page. No card is charged.
        </div>
        <div className="mt-4 rounded-2xl bg-white p-8 shadow-sm">
          <p className="text-sm text-gray-500">Pay {ENTITIES.platform.legalName}</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums">{cadExact(order.total_cents)} <span className="text-base font-normal text-gray-500">CAD</span></p>
          <p className="mt-1 text-xs text-gray-500">Statement descriptor: {ENTITIES.platform.statementDescriptor}</p>
          {order.status !== "pending" ? (
            <p className="mt-6 rounded-lg bg-gray-100 p-3 text-sm">This order is already {order.status}.</p>
          ) : (
            <form action={payMock} className="mt-6 space-y-3">
              <input type="hidden" name="orderId" value={order.id} />
              <label className="block text-sm font-medium text-gray-700">Card number
                <input className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono" defaultValue="4242 4242 4242 4242" readOnly />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block text-sm font-medium text-gray-700">Expiry<input className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono" defaultValue="12 / 30" readOnly /></label>
                <label className="block text-sm font-medium text-gray-700">CVC<input className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono" defaultValue="123" readOnly /></label>
              </div>
              {declined && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">Your card was declined (simulated). Nothing was charged.</p>}
              <button name="outcome" value="pay" className="w-full rounded-lg bg-[#0f1f1b] py-3 font-semibold text-white">Pay {cadExact(order.total_cents)}</button>
              <button name="outcome" value="decline" className="w-full rounded-lg border border-gray-300 py-2 text-sm text-gray-600">Simulate a declined card</button>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
