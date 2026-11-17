#!/usr/bin/env node
/**
 * RECLAIM compliance linter — runs before every build (npm run build → prebuild).
 *
 * Turns the website's regulatory design rules into checks that fail the build.
 * It is a guard-rail, not legal sign-off: it catches the mistakes that are easy
 * to make in copy and code. See docs/COMPLIANCE_REGISTER.md for the authority
 * behind each rule.
 */
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const errors = [];
const warnings = [];
const rel = (p) => relative(root, p);

function walk(dir, exts) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return walk(p, exts);
    return exts.some((e) => p.endsWith(e)) ? [p] : [];
  });
}

// ── Scope: everything a member of the public can see without logging in ─────
const PUBLIC_FILES = [
  ...walk(join(root, "app/(site)"), [".tsx", ".ts"]),
  ...["SiteHeader.tsx", "SiteFooter.tsx", "BlueprintCard.tsx", "forms.tsx", "ui.tsx"].map((f) => join(root, "components", f)),
  join(root, "content/articles.ts"),
  join(root, "content/legal.ts"),
  join(root, "config/catalog.ts"),
  join(root, "config/partners.ts"),
].filter(existsSync);

// Rule 1 — no prescription drug, brand or peptide product names in public content
// (Food and Drug Regulations C.01.044; O. Reg. 114/94 s.6(2); Health Canada advisories 2025–26).
const PRODUCT_NAMES = [
  "semaglutide", "tirzepatide", "liraglutide", "dulaglutide", "retatrutide", "cagrilintide", "orforglipron", "survodutide",
  "ozempic", "wegovy", "rybelsus", "mounjaro", "zepbound", "saxenda", "victoza", "trulicity",
  "contrave", "naltrexone", "bupropion", "phentermine", "orlistat", "xenical", "metformin",
  "bpc-157", "bpc157", "tb-500", "tb500", "ipamorelin", "cjc-1295", "sermorelin", "tesamorelin", "aod-9604", "mots-c", "klow",
  "glp-1", "glp1", "testosterone", "hgh", "growth hormone",
];
// Rule 2 — prohibited claim language (O. Reg. 114/94 s.6; CPSO Advertising Responsibly; Competition Act).
const CLAIMS = [
  [/\bguarantee(d|s)?\b/i, "guarantee"], [/\bmiracle\b/i, "miracle"], [/\brisk[- ]free\b/i, "risk-free"],
  [/\bclinically proven\b/i, "clinically proven"], [/#1\b/, "#1"], [/\b(the )?best\b/i, "superlative 'best'"],
  [/\bleading\b/i, "superlative 'leading'"], [/\btop[- ]rated\b/i, "superlative 'top-rated'"],
  [/\blose \d+\s?(lb|lbs|pounds|kg|kilos)\b/i, "numeric weight-loss promise"], [/\bdetox\b/i, "detox"], [/\bmelt (away )?fat\b/i, "melt fat"],
  [/★★★★★/, "star-rating testimonial"], [/\bstack(s)?\b/i, "'stack' (experimental combinations)"], [/research use only/i, "'research use only'"],
];
// Rule 3 — no treatment/cure claims for Schedule A.1 conditions (Food and Drugs Act s.3).
const SCHED_A1 = /(obesity|obese|diabetes|diabetic|hypertension|depression|cancer|asthma|arthritis|dementia|thyroid disease)/i;
const TREAT = /\b(treat|treats|treatment|cure|cures|prevent|prevents|reverse|reverses|manage|manages)\b/i;

for (const file of PUBLIC_FILES) {
  const lines = readFileSync(file, "utf8").split("\n");
  lines.forEach((line, i) => {
    const code = line
      .replace(/\/\/.*$/, "").replace(/^\s*\*.*$/, "") // ignore comments
      .replace(/className=(\{`[^`]*`\}|"[^"]*")/g, ""); // ignore Tailwind class names (e.g. leading-7)
    const lower = code.toLowerCase();
    for (const name of PRODUCT_NAMES) {
      const re = new RegExp(`(^|[^a-z0-9])${name.replace(/[-+]/g, (c) => `\\${c}`)}([^a-z0-9]|$)`, "i");
      if (re.test(lower)) errors.push(`${rel(file)}:${i + 1}  product name "${name}" in public content`);
    }
    for (const [re, label] of CLAIMS) if (re.test(code)) errors.push(`${rel(file)}:${i + 1}  prohibited claim language: ${label}`);
    if (SCHED_A1.test(code) && TREAT.test(code)) {
      const words = code.split(/\s+/);
      const a = words.findIndex((w) => SCHED_A1.test(w));
      const t = words.findIndex((w) => TREAT.test(w));
      if (a >= 0 && t >= 0 && Math.abs(a - t) <= 8) errors.push(`${rel(file)}:${i + 1}  Schedule A.1 condition near treatment language`);
    }
    // Rule 4 — prices must come from the catalogue (rendered with cad()), never hard-coded in public JSX.
    if (/\.tsx$/.test(file) && />[^<{]*\$\d/.test(code)) errors.push(`${rel(file)}:${i + 1}  hard-coded price — render prices from config/catalog.ts`);
  });
}

// Rule 5 — public videos: same product-name rule applied to titles, summaries and captions.
const videos = JSON.parse(readFileSync(join(root, "content/videos.json"), "utf8"));
for (const v of videos) {
  const text = [v.title, v.summary, ...v.cues.map((c) => c.text)].join(" ").toLowerCase();
  for (const name of PRODUCT_NAMES) if (text.includes(name)) errors.push(`content/videos.json  video "${v.id}" mentions "${name}"`);
  // Accessibility: every video needs captions and chapters (AODA / WCAG 1.2.2).
  if (!v.cues?.length) errors.push(`content/videos.json  video "${v.id}" has no captions`);
  const dir = v.access === "public" ? join(root, "public/media/public", v.id) : join(root, "media/members", v.id);
  for (const f of ["video.mp4", "captions.vtt", "poster.jpg"]) if (!existsSync(join(dir, f))) errors.push(`${rel(dir)}/${f} missing — run npm run media`);
}

// Rule 6 — store boundary: only lib/clinical opens the clinical store; only lib/pharmacy opens the pharmacy store.
for (const file of walk(join(root, "app"), [".ts", ".tsx"]).concat(walk(join(root, "lib"), [".ts"]), walk(join(root, "components"), [".tsx", ".ts"]))) {
  const r = rel(file);
  const src = readFileSync(file, "utf8");
  if (/db\(\s*["']clinical["']\s*\)/.test(src) && !r.startsWith("lib/clinical/") && !r.startsWith("lib/db/")) errors.push(`${r}  opens the clinical store outside lib/clinical`);
  if (/db\(\s*["']pharmacy["']\s*\)/.test(src) && !r.startsWith("lib/pharmacy/") && !r.startsWith("lib/db/")) errors.push(`${r}  opens the pharmacy store outside lib/pharmacy`);
  if (/(lib\/pharmacy\/|lib\/clinical\/)/.test(r) && /from ["']@\/lib\/commerce["']/.test(src)) errors.push(`${r}  clinical/pharmacy code must not import commerce (membership must not influence care or drug prices)`);
  // Rule 7 — no third-party trackers anywhere.
  if (/(googletagmanager|google-analytics|gtag\(|fbq\(|connect\.facebook|hotjar|segment\.com|tiktok\.com\/i18n|doubleclick)/i.test(src)) errors.push(`${r}  third-party tracker detected`);
  // Rule 8 — marketing consent must never be pre-ticked (CASL).
  if (/name=["'](marketing|analytics|research)["'][^>]*defaultChecked/.test(src)) errors.push(`${r}  optional consent pre-ticked`);
}

// Rule 9 — catalogue integrity: platform sells only non-pharmacy, non-insured items, each with tax code and price status.
const catalog = readFileSync(join(root, "config/catalog.ts"), "utf8");
const planBlocks = catalog.split(/\n  \{\n    id: "/).slice(1);
for (const b of planBlocks) {
  const id = b.slice(0, b.indexOf('"'));
  if (!/merchant: "platform"/.test(b)) errors.push(`config/catalog.ts  "${id}" must be sold by the platform entity`);
  if (!/taxCode: "/.test(b)) errors.push(`config/catalog.ts  "${id}" has no tax code`);
  if (/(includes|description)[\s\S]*\b(medication|prescription|consult(ation)? with (a )?(physician|doctor))\b/i.test(b.split("limits")[0] ?? "")) errors.push(`config/catalog.ts  "${id}" appears to bundle medical care or medication into a membership`);
  if (/priceStatus: "hypothesis"/.test(b)) warnings.push(`config/catalog.ts  "${id}" price is still a hypothesis`);
}

// Rule 10 — published health articles need a clinical reviewer and date.
const articles = readFileSync(join(root, "content/articles.ts"), "utf8");
const drafts = (articles.match(/status: "draft",/g) ?? []).length;
if (/status: "published",\s*\n\s*reviewer: null/.test(articles)) errors.push("content/articles.ts  published article without clinical reviewer");
if (drafts) warnings.push(`content/articles.ts  ${drafts} article(s) awaiting clinical review (shown with a draft banner)`);

// ── Report ───────────────────────────────────────────────────────────────────
const uniq = (a) => [...new Set(a)];
for (const w of uniq(warnings)) console.log(`  warn  ${w}`);
for (const e of uniq(errors)) console.log(`  ERROR ${e}`);
console.log(`\ncompliance-lint: ${uniq(errors).length} error(s), ${uniq(warnings).length} warning(s) across ${PUBLIC_FILES.length} public files and ${videos.length} videos`);
if (errors.length) process.exit(1);
