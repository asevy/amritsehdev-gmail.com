import Link from "next/link";
import type { EntityId } from "@/config/site";
import { ENTITIES } from "@/config/site";

export function Container({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`mx-auto w-full max-w-6xl px-5 sm:px-8 ${className}`}>{children}</div>;
}

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
        <circle cx="13" cy="13" r="10" fill="none" stroke={inverted ? "#2b3b36" : "#e2ddd1"} strokeWidth="4" />
        <path d="M13 3 A10 10 0 1 1 3.6 16.4" fill="none" stroke={inverted ? "#d8f26a" : "#0f1f1b"} strokeWidth="4" strokeLinecap="round" />
        <circle cx="13" cy="13" r="2.6" fill={inverted ? "#d8f26a" : "#b9461f"} />
      </svg>
      <span className={`text-[15px] font-semibold tracking-[0.22em] ${inverted ? "text-paper" : "text-ink"}`}>RECLAIM</span>
    </span>
  );
}

const ENTITY_STYLE: Record<EntityId, string> = {
  platform: "border-moss/30 bg-moss-soft text-moss",
  clinical: "border-clinic/30 bg-clinic-soft text-clinic",
  pharmacy: "border-rx/30 bg-rx-soft text-rx",
};
const ENTITY_SHORT: Record<EntityId, string> = {
  platform: "RECLAIM",
  clinical: "Medical practice",
  pharmacy: "Pharmacy",
};

/** Every price, record and message on the site is attributed to exactly one legal entity. */
export function EntityTag({ entity, label }: { entity: EntityId; label?: string }) {
  return (
    <span className={`chip ${ENTITY_STYLE[entity]}`} title={ENTITIES[entity].legalName}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      {label ?? ENTITY_SHORT[entity]}
    </span>
  );
}

export function DraftBadge({ children = "Draft — counsel review required" }: { children?: React.ReactNode }) {
  return <span className="chip border-warn/30 bg-warn-soft text-warn">{children}</span>;
}

export function HypothesisBadge() {
  return (
    <span className="chip border-warn/30 bg-warn-soft text-warn" title="Not yet validated by cost-to-serve, supplier quotes or willingness-to-pay testing">
      Pilot price
    </span>
  );
}

export function Notice({ tone = "info", title, children }: { tone?: "info" | "warn" | "danger" | "clinical"; title?: string; children: React.ReactNode }) {
  const styles = {
    info: "border-line bg-bone/60",
    warn: "border-warn/30 bg-warn-soft/60",
    danger: "border-ember/40 bg-ember-soft/70",
    clinical: "border-clinic/30 bg-clinic-soft/60",
  }[tone];
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm leading-6 ${styles}`} role={tone === "danger" ? "alert" : undefined}>
      {title && <p className="mb-0.5 font-semibold">{title}</p>}
      <div className="text-ink-2">{children}</div>
    </div>
  );
}

export function EmergencyNotice() {
  return (
    <Notice tone="danger" title="Not for emergencies">
      If you think you are having a medical emergency, call <strong>911</strong> or go to the nearest emergency department. If you are in crisis or thinking about suicide, call or text <strong>9-8-8</strong>.
    </Notice>
  );
}

export function SectionHeading({ eyebrow, title, children, className = "" }: { eyebrow?: string; title: React.ReactNode; children?: React.ReactNode; className?: string }) {
  return (
    <div className={`max-w-2xl ${className}`}>
      {eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}
      <h2 className="text-3xl font-medium leading-[1.1] sm:text-[40px]">{title}</h2>
      {children && <div className="mt-4 text-[17px] leading-7 text-ink-2">{children}</div>}
    </div>
  );
}

export function ArrowLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="group inline-flex items-center gap-1.5 text-sm font-semibold text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
      {children}
      <span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">→</span>
    </Link>
  );
}

export function Stat({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className="mt-1 font-mono text-2xl font-medium tabular-nums">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}
