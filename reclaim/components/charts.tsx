"use client";

import { useRef, useState } from "react";

/**
 * Single-series line chart (no legend: the title names the series).
 * Specs follow the dataviz skill: 2px line, ≥8px end marker with a 2px surface ring,
 * hairline solid gridlines, value label at the line end only, crosshair + tooltip on hover,
 * and a reference "target" line labelled in text tokens. A data table is rendered by the caller.
 */
export function LineChart({
  points, unit, target, decimals = 1, height = 168, ariaLabel,
}: {
  points: { t: string; v: number }[];
  unit: string;
  target?: number | null;
  decimals?: number;
  height?: number;
  ariaLabel: string;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  if (points.length === 0) return <p className="text-sm text-muted">No data yet.</p>;

  const W = 520, H = height, padL = 44, padR = 88, padT = 16, padB = 24;
  const xs = points.map((p) => new Date(p.t).getTime());
  const vals = points.map((p) => p.v).concat(target != null ? [target] : []);
  const rawMin = Math.min(...vals), rawMax = Math.max(...vals);
  // "Nice" axis: round tick step (1, 2, 2.5, 5 × 10^k) and bounds snapped to it.
  const rough = (rawMax - rawMin || Math.abs(rawMax) * 0.1 || 1) / 3;
  const mag = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= rough) ?? 10 * mag;
  const min = Math.floor(rawMin / step) * step;
  const max = Math.ceil(rawMax / step) * step === rawMax ? rawMax + step : Math.ceil(rawMax / step) * step;
  const x0 = Math.min(...xs), x1 = Math.max(...xs) || x0 + 1;
  const sx = (t: number) => padL + ((t - x0) / (x1 - x0 || 1)) * (W - padL - padR);
  const sy = (v: number) => padT + (1 - (v - min) / (max - min)) * (H - padT - padB);
  const ticks: number[] = [];
  for (let t = min; t <= max + step / 2; t += step) ticks.push(Number(t.toFixed(6)));
  const fmt = (v: number) => v.toLocaleString("en-CA", { maximumFractionDigits: decimals, minimumFractionDigits: 0 });
  const path = points.map((p, i) => `${i ? "L" : "M"}${sx(xs[i]).toFixed(1)},${sy(p.v).toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  const hp = hover != null ? points[hover] : null;

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const svg = ref.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    xs.forEach((t, i) => { if (Math.abs(sx(t) - x) < Math.abs(sx(xs[best]) - x)) best = i; });
    setHover(best);
  };

  return (
    <div className="relative">
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} className="w-full touch-none" role="img" aria-label={ariaLabel} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={padL} x2={W - padR} y1={sy(t)} y2={sy(t)} stroke="#ece8de" strokeWidth={1} />
            <text x={padL - 6} y={sy(t) + 3.5} textAnchor="end" fontSize="10" fill="#56645f" style={{ fontVariantNumeric: "tabular-nums" }}>{fmt(t)}</text>
          </g>
        ))}
        {target != null && (
          <g>
            <line x1={padL} x2={W - padR} y1={sy(target)} y2={sy(target)} stroke="#56645f" strokeWidth={1} opacity={0.6} />
            <text x={padL + 4} y={sy(target) - 4} fontSize="10" fill="#56645f">Target {fmt(target)}</text>
          </g>
        )}
        <path d={path} fill="none" stroke="var(--color-series)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={sx(xs[xs.length - 1])} cy={sy(last.v)} r={4} fill="var(--color-series)" stroke="#fff" strokeWidth={2} />
        <text x={sx(xs[xs.length - 1]) + 8} y={sy(last.v) - 8} fontSize="11" fontWeight={600} fill="#0f1f1b">{fmt(last.v)} {unit}</text>
        <text x={padL} y={H - 6} fontSize="10" fill="#56645f">{new Date(x0).toLocaleDateString("en-CA", { month: "short", day: "numeric" })}</text>
        <text x={W - padR} y={H - 6} fontSize="10" fill="#56645f" textAnchor="end">{new Date(x1).toLocaleDateString("en-CA", { month: "short", day: "numeric" })}</text>
        {hp && hover != null && (
          <g>
            <line x1={sx(xs[hover])} x2={sx(xs[hover])} y1={padT} y2={H - padB} stroke="#cfc8b9" strokeWidth={1} />
            <circle cx={sx(xs[hover])} cy={sy(hp.v)} r={5} fill="var(--color-series)" stroke="#fff" strokeWidth={2} />
          </g>
        )}
      </svg>
      {hp && hover != null && (
        <div
          className="pointer-events-none absolute top-0 rounded-lg border border-line bg-card px-2.5 py-1.5 text-xs shadow-sm"
          style={{ left: `${(sx(xs[hover]) / W) * 100}%`, transform: "translateX(-50%)" }}
        >
          <span className="text-muted">{new Date(hp.t).toLocaleDateString("en-CA", { month: "short", day: "numeric" })}</span>{" "}
          <span className="font-semibold">{fmt(hp.v)} {unit}</span>
        </div>
      )}
    </div>
  );
}

/** Horizontal single-series bars: ≤ 24px thick (12px here), 4px rounded data end, value at the tip, per-bar hover. */
export function BarList({ rows, format = (v: number) => v.toLocaleString("en-CA") }: { rows: { label: string; value: number; note?: string }[]; format?: (v: number) => string }) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <ul className="space-y-2.5">
      {rows.map((r, i) => (
        <li key={r.label} className="grid grid-cols-[140px_1fr] items-center gap-3 text-sm" onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}>
          <span className="truncate text-ink-2" title={r.label}>{r.label}</span>
          <span className="relative flex items-center gap-2">
            <span className="h-3 rounded-r-[4px]" style={{ width: `${Math.max(0.5, (r.value / max) * 82)}%`, background: "var(--color-series)", opacity: hover == null || hover === i ? 1 : 0.55 }} />
            <span className="font-medium tabular-nums">{format(r.value)}</span>
            {hover === i && r.note && <span className="absolute -top-7 left-0 z-10 whitespace-nowrap rounded-md border border-line bg-card px-2 py-1 text-xs shadow-sm">{r.note}</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}
