import Link from "next/link";
import { Container, Logo } from "./ui";
import { currentUser, homeFor } from "@/lib/auth";

const NAV = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/programmes", label: "Programmes & pricing" },
  { href: "/medical-care", label: "Medical care" },
  { href: "/network", label: "Local network" },
  { href: "/learn", label: "Learn" },
  { href: "/employers", label: "Employers" },
];

export async function SiteHeader() {
  const user = await currentUser();
  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-paper/90 backdrop-blur">
      <Container className="flex h-16 items-center justify-between gap-6">
        <Link href="/" aria-label="RECLAIM home">
          <Logo />
        </Link>
        <nav aria-label="Main" className="hidden items-center gap-6 lg:flex">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="text-[14px] font-medium text-ink-2 hover:text-ink">
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {user ? (
            <Link href={homeFor(user.role)} className="btn-ghost btn-sm">
              {user.role === "member" ? "My portal" : "Workspace"}
            </Link>
          ) : (
            <Link href="/login" className="hidden text-[14px] font-medium text-ink-2 hover:text-ink sm:inline">
              Log in
            </Link>
          )}
          <Link href="/assessment" className="btn-primary btn-sm whitespace-nowrap">
            <span className="hidden sm:inline">Free&nbsp;</span>assessment
          </Link>
          <details className="relative lg:hidden">
            <summary className="btn-ghost btn-sm list-none" aria-label="Open menu">
              Menu
            </summary>
            <div className="absolute right-0 mt-2 w-64 rounded-2xl border border-line bg-card p-2 shadow-lg">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className="block rounded-lg px-3 py-2 text-sm hover:bg-bone">
                  {n.label}
                </Link>
              ))}
              {!user && (
                <Link href="/login" className="block rounded-lg px-3 py-2 text-sm hover:bg-bone">
                  Log in
                </Link>
              )}
            </div>
          </details>
        </div>
      </Container>
    </header>
  );
}
