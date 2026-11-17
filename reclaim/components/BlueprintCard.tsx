/** Illustrative (non-data) visual of a member's Blueprint, used on marketing pages. Labelled as illustrative. */
export function BlueprintCard() {
  const targets = [
    { label: "Sit-to-stand (30 s)", from: "11", to: "15", pct: 0.75 },
    { label: "Waist", from: "104 cm", to: "98 cm", pct: 0.55 },
    { label: "Daily steps", from: "5,200", to: "8,000", pct: 0.8 },
  ];
  return (
    <div className="relative">
      <div className="absolute -inset-4 -z-10 rounded-[28px] bg-bone grid-paper" aria-hidden="true" />
      <figure className="rounded-3xl bg-ink p-6 text-paper shadow-[0_30px_60px_-30px_rgba(15,31,27,0.6)]">
        <div className="flex items-center justify-between">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-paper/60">Your Blueprint · v2</p>
          <span className="rounded-full border border-paper/20 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-paper/60">Illustrative</span>
        </div>
        <div className="mt-5 flex items-center gap-5">
          <svg width="92" height="92" viewBox="0 0 92 92" role="img" aria-label="Week 9 of 16">
            <circle cx="46" cy="46" r="38" fill="none" stroke="#2b3b36" strokeWidth="9" />
            <circle cx="46" cy="46" r="38" fill="none" stroke="#d8f26a" strokeWidth="9" strokeLinecap="round" strokeDasharray={`${(9 / 16) * 238.8} 238.8`} transform="rotate(-90 46 46)" />
            <text x="46" y="44" textAnchor="middle" fill="#faf8f3" fontSize="20" fontFamily="var(--font-geist-mono)">9/16</text>
            <text x="46" y="60" textAnchor="middle" fill="#9fb3ac" fontSize="9" fontFamily="var(--font-geist-mono)">WEEKS</text>
          </svg>
          <div className="text-sm leading-6 text-paper/80">
            <p className="font-display text-xl text-paper">3 sessions · 40 min</p>
            <p>Home + partner gym · protein at breakfast · 6:30 wake time</p>
          </div>
        </div>
        <ul className="mt-6 space-y-4">
          {targets.map((t) => (
            <li key={t.label}>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-paper/85">{t.label}</span>
                <span className="font-mono text-xs text-paper/60">
                  {t.from} → <span className="text-lime">{t.to}</span>
                </span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-ink-2">
                <div className="h-1.5 rounded-full bg-lime" style={{ width: `${t.pct * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
        <figcaption className="mt-6 border-t border-paper/10 pt-4 text-xs leading-5 text-paper/55">
          Targets are set with your coach and re-measured every four weeks. Example only — not a member&apos;s data or a predicted result.
        </figcaption>
      </figure>
    </div>
  );
}
