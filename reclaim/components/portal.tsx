import Link from "next/link";

export function PageHeader({ eyebrow, title, children, actions }: { eyebrow?: React.ReactNode; title: string; children?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
        <h1 className="text-4xl font-medium leading-tight">{title}</h1>
        {children && <div className="mt-2 text-[15px] leading-7 text-ink-2">{children}</div>}
      </div>
      {actions}
    </header>
  );
}

export function Panel({ title, children, action, className = "" }: { title?: React.ReactNode; children: React.ReactNode; action?: React.ReactNode; className?: string }) {
  return (
    <section className={`card p-5 ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="font-sans text-[15px] font-semibold tracking-normal">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function MembershipRequired() {
  return (
    <div className="card p-8 text-center">
      <p className="eyebrow">Members only</p>
      <h2 className="mt-3 text-3xl">This part of RECLAIM comes with a membership.</h2>
      <p className="mx-auto mt-3 max-w-md text-ink-2">Your free account still includes Care (medical practice) and Privacy. A membership adds your Blueprint, coach, plan, progress, form checks and your record.</p>
      <Link href="/programmes" className="btn-primary mt-6">See programmes</Link>
    </div>
  );
}

export function Flash({ children, tone = "ok" }: { children: React.ReactNode; tone?: "ok" | "err" }) {
  return <p role="status" className={`mb-6 rounded-xl px-4 py-3 text-sm ${tone === "ok" ? "bg-moss-soft text-moss" : "bg-ember-soft text-ember"}`}>{children}</p>;
}
