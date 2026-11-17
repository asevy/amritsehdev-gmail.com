"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const GROUPS = [
  {
    label: "Programme",
    entity: "platform",
    items: [
      ["/portal", "Today"],
      ["/portal/blueprint", "Blueprint"],
      ["/portal/plan", "This week"],
      ["/portal/progress", "Progress"],
      ["/portal/library", "Video library"],
      ["/portal/appointments", "Appointments"],
      ["/portal/messages", "Coach messages"],
      ["/portal/network", "Local network"],
    ],
  },
  { label: "Medical practice", entity: "clinical", items: [["/portal/care", "Care & prescriptions"]] },
  { label: "Account", entity: "platform", items: [["/portal/billing", "Billing"], ["/portal/privacy", "Privacy & data"]] },
];

const MEMBER_ONLY = new Set(["/portal/plan", "/portal/library", "/portal/messages", "/portal/network", "/portal/progress", "/portal/blueprint", "/portal/appointments"]);

export function PortalNav({ hasMembership }: { hasMembership: boolean }) {
  const path = usePathname();
  return (
    <nav aria-label="Portal" className="mt-6 space-y-5">
      {GROUPS.map((g) => (
        <div key={g.label}>
          <p className={`eyebrow mb-1.5 px-2 ${g.entity === "clinical" ? "!text-clinic" : ""}`}>{g.label}</p>
          <ul className="space-y-0.5">
            {g.items.map(([href, label]) => {
              const active = href === "/portal" ? path === href : path.startsWith(href);
              const locked = !hasMembership && MEMBER_ONLY.has(href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center justify-between rounded-lg px-2 py-1.5 text-sm ${active ? "bg-ink text-paper" : "text-ink-2 hover:bg-bone"}`}
                  >
                    {label}
                    {locked && <span className="text-[10px] uppercase tracking-wider opacity-60">members</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
