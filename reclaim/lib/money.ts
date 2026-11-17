export function cad(cents: number, opts: { showZero?: boolean } = {}): string {
  if (cents === 0 && !opts.showZero) return "$0";
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", minimumFractionDigits: cents % 100 === 0 ? 0 : 2 }).format(cents / 100);
}

export function cadExact(cents: number): string {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", minimumFractionDigits: 2 }).format(cents / 100);
}

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric", year: "numeric" }): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto", ...opts }).format(new Date(iso));
}

export function fmtDateTime(iso: string | null | undefined): string {
  return fmtDate(iso, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
