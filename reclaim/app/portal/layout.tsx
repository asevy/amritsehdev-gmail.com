import Link from "next/link";
import { Logo } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { activeSubscription } from "@/lib/commerce";
import { planById } from "@/config/catalog";
import { logout } from "@/app/actions/auth";
import { PortalNav } from "./PortalNav";
import { SITE } from "@/config/site";

export default async function PortalLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser(["member"]);
  const sub = activeSubscription(user.id);
  const plan = sub ? planById(sub.plan_id) : null;
  return (
    <div className="min-h-screen bg-paper lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="border-b border-line bg-card lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
        <div className="flex h-full flex-col p-5">
          <Link href="/" aria-label="RECLAIM home"><Logo /></Link>
          <div className="mt-6 rounded-xl bg-bone/70 p-3">
            <p className="text-sm font-semibold">{user.name}</p>
            <p className="mt-0.5 text-xs text-muted">
              {plan ? `${plan.name} membership${sub?.status === "paused" ? " · paused" : sub?.cancel_at_period_end ? " · ends soon" : ""}` : "Free account — no membership"}
            </p>
          </div>
          <PortalNav hasMembership={!!sub} />
          <div className="mt-auto space-y-3 pt-6">
            <p className="text-[11px] leading-4 text-muted">{SITE.emergency}</p>
            <form action={logout}><button className="text-sm text-muted underline hover:text-ink">Log out</button></form>
          </div>
        </div>
      </aside>
      <main id="main" className="min-w-0">
        <div className="mx-auto max-w-5xl px-5 py-8 sm:px-8 lg:py-10">{children}</div>
      </main>
    </div>
  );
}
