import Link from "next/link";
import { requireUser } from "@/lib/auth";
import { Logo, EntityTag } from "@/components/ui";
import { logout } from "@/app/actions/auth";

const ENTITY_FOR = { clinician: "clinical", pharmacist: "pharmacy", coach: "platform" } as const;
const TITLE = { clinician: "Clinician desk", pharmacist: "Pharmacy desk", coach: "Coach desk" } as const;

export default async function StaffLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser(["clinician", "pharmacist", "coach"]);
  const role = user.role as keyof typeof TITLE;
  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line bg-card">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-5">
          <div className="flex items-center gap-4"><Link href="/"><Logo /></Link><span className="text-sm font-semibold">{TITLE[role]}</span><EntityTag entity={ENTITY_FOR[role]} /></div>
          <div className="flex items-center gap-4 text-sm"><span className="text-muted">{user.name}</span><form action={logout}><button className="underline">Log out</button></form></div>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-5 py-8">{children}</main>
    </div>
  );
}
