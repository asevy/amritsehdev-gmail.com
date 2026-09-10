"""Claim Explorer - renders the ledger as a browsable HTML page.

The graph shouldn't just exist; researchers browse it. Every claim card
shows the full record - subject, predicate, object, status, sources,
approval, supersession - plus the live evidence-path check, and links
click through: claim -> entity -> source -> citing claims.

Usage: python3 explorer.py [data_dir] [out_file]
Default: reads ./data, writes ./explorer.html
"""
from __future__ import annotations

import datetime
import html
import sys

from schema import evidence_path_gaps, freshness
from store import Ledger

TODAY = datetime.date.today().isoformat()

CSS = """
:root{--paper:#FBF9F4;--panel:#F5F2E9;--ink:#1A1A18;--muted:#6E6A60;
--green:#16382B;--navy:#14263D;--burgundy:#6E2C35;--rule:#DED9CC;
--ok:#2E5E45;}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
--paper:#111714;--panel:#161D19;--ink:#EAE5D8;--muted:#98948A;
--green:#8FB3A1;--navy:#93ACC7;--burgundy:#C48D96;--rule:#2A322D;
--ok:#7FB093;}}
:root[data-theme="dark"]{--paper:#111714;--panel:#161D19;--ink:#EAE5D8;
--muted:#98948A;--green:#8FB3A1;--navy:#93ACC7;--burgundy:#C48D96;
--rule:#2A322D;--ok:#7FB093;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
font:400 14px/1.55 Inter,-apple-system,"Helvetica Neue",sans-serif;}
a{color:var(--green);text-decoration:none}
a:hover{text-decoration:underline}
header{position:sticky;top:0;background:var(--paper);z-index:3;
border-bottom:1px solid var(--rule);padding:14px 26px;
display:flex;gap:22px;align-items:baseline;flex-wrap:wrap}
.wordmark{font:600 12px/1 Inter;letter-spacing:.22em;text-transform:uppercase}
.stat{font-size:12.5px;color:var(--muted)}
.stat b{color:var(--ink);font-variant-numeric:tabular-nums}
main{max-width:900px;margin:0 auto;padding:30px 22px 80px}
h2{font:600 12px/1 Inter;letter-spacing:.18em;text-transform:uppercase;
color:var(--muted);margin:38px 0 14px;padding-bottom:8px;
border-bottom:1px solid var(--rule)}
.card{border:1px solid var(--rule);border-radius:4px;background:var(--panel);
padding:14px 18px;margin:0 0 12px;scroll-margin-top:70px}
.card:target{border-color:var(--burgundy)}
.cardhead{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;
margin-bottom:8px}
.cid{font:600 12px/1 ui-monospace,Menlo,monospace;color:var(--muted)}
.pill{font:600 10px/1 Inter;letter-spacing:.1em;text-transform:uppercase;
padding:3px 8px;border-radius:999px;border:1px solid var(--rule)}
.APPROVED{color:var(--ok);border-color:var(--ok)}
.PROPOSED{color:var(--navy);border-color:var(--navy)}
.LEAD{color:var(--muted)}
.SUPERSEDED,.RETRACTED{color:var(--muted);text-decoration:line-through}
dl{display:grid;grid-template-columns:150px 1fr;gap:4px 14px;margin:0}
dt{font:500 10.5px/1.6 Inter;letter-spacing:.12em;text-transform:uppercase;
color:var(--muted)}
dd{margin:0;overflow-wrap:anywhere}
.path-ok{color:var(--ok)}
.path-gap{color:var(--burgundy)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{border:1px solid var(--rule);border-radius:999px;padding:4px 12px;
font-size:12.5px;background:var(--panel)}
.chip small{color:var(--muted)}
.muted{color:var(--muted)}
footer{max-width:900px;margin:0 auto;padding:0 22px 40px;
font-size:12px;color:var(--muted);border-top:1px solid var(--rule);
padding-top:14px}
@media(max-width:640px){dl{grid-template-columns:1fr}dt{margin-top:6px}}
"""


def esc(x) -> str:
    return html.escape(str(x))


def link_entity(led, eid):
    if eid in led.entities:
        return f'<a href="#e-{esc(eid)}">{esc(led.entities[eid].name)}</a>'
    return esc(eid)


def render_object(led, obj):
    if isinstance(obj, dict):
        parts = []
        for k, v in obj.items():
            v_html = link_entity(led, v) if isinstance(v, str) and \
                v in led.entities else esc(v)
            parts.append(f"<b>{esc(k)}</b>: {v_html}")
        return " · ".join(parts)
    if isinstance(obj, str) and obj in led.entities:
        return link_entity(led, obj)
    return esc(obj)


FRESH_COLOR = {"current": "var(--ok)", "aging": "var(--navy)",
               "stale": "var(--burgundy)", "superseded": "var(--muted)"}


def claim_card(led, c) -> str:
    gaps = evidence_path_gaps(c, led.sources, led.extractions)
    path = ('<span class="path-ok">complete</span>' if not gaps else
            '<span class="path-gap">incomplete — ' +
            "; ".join(esc(g) for g in gaps) + "</span>")
    srcs = ", ".join(f'<a href="#s-{esc(s)}">{esc(s)}</a>'
                     for s in c.sources) or '<span class="muted">—</span>'
    rows = [
        ("Subject", link_entity(led, c.subject)),
        ("Predicate", esc(c.predicate)),
        ("Object", render_object(led, c.object)),
        ("Valid", esc(f"{c.valid_from or '—'} → {c.valid_to or 'present'}")),
        ("Sources", srcs),
        ("Analyst", esc(c.analyst) or '<span class="muted">—</span>'),
        ("Verified", esc(c.verified_date or "pending")),
        ("Methodology", esc(c.methodology_version) or
         '<span class="muted">—</span>'),
        ("Superseded by",
         f'<a href="#c-{esc(c.superseded_by)}">{esc(c.superseded_by)}</a>'
         if c.superseded_by else '<span class="muted">—</span>'),
        ("Evidence path", path),
        ("Freshness", (lambda f: f'<span style="color:'
                       f'{FRESH_COLOR[f]}">{f}</span>')(
            freshness(c, TODAY))),
    ]
    if c.extractions:
        rows.insert(5, ("Extractions", " · ".join(
            f'<a href="#x-{esc(x)}">{esc(x)}</a>'
            for x in c.extractions)))
    if c.block_id:
        rows.insert(3, ("Block", esc(c.block_id)))
    if c.registry_verbatim:
        rows.insert(3, ("Registry verbatim", esc(c.registry_verbatim)))
    if c.statutory_basis:
        rows.insert(4, ("Statutory basis", esc(c.statutory_basis)))
    if c.notes:
        rows.append(("Notes", esc(c.notes)))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    return (f'<div class="card" id="c-{esc(c.id)}">'
            f'<div class="cardhead"><span class="cid">{esc(c.id)}</span>'
            f'<span class="pill {esc(c.status)}">{esc(c.status)}</span>'
            f'</div><dl>{dl}</dl></div>')


EDGE_WORDS = ("shareholder", "owner", "owns", "control",
              "heritage", "founder", "beneficial_interest")


def _entity_refs(led, obj):
    if isinstance(obj, str) and obj in led.entities:
        return [obj]
    if isinstance(obj, dict):
        return [v for v in obj.values()
                if isinstance(v, str) and v in led.entities]
    return []


def _abbr_shares(s):
    try:
        n = float(str(s).replace(",", ""))
    except ValueError:
        return str(s)
    if n >= 1e9:
        return f"{n/1e9:.3f}B sh"
    if n >= 1e6:
        return f"{n/1e6:.1f}M sh"
    return f"{n:,.0f} sh"


def ownership_view(led, scope=None):
    """Edges for the default graph: WHO OWNS WHAT *NOW*, in three
    layers — family attribution (incl. the explicit unresolved
    blocker), current ownership, and events as annotations on the
    ownership edge they changed. History (valid_to set) stays in the
    timeline; ordinary LEADs stay off the graph; transactions are never
    nodes."""
    events = [c for c in led.claims.values()
              if c.predicate == "material_ownership_change"
              and c.status in ("PROPOSED", "APPROVED")]
    edges = []
    for c in led.claims.values():
        if c.status in ("SUPERSEDED", "RETRACTED", "REJECTED"):
            continue
        if not any(w in c.predicate for w in EDGE_WORDS):
            continue
        subj = led.entities.get(c.subject)
        if subj is None or subj.type == "transaction":
            continue
        blocker = c.predicate.endswith("_unresolved")
        if c.status == "LEAD" and not blocker:
            continue
        if c.valid_to and not blocker:
            continue  # historical point — timeline's job
        for held in _entity_refs(led, c.object):
            if led.entities[held].type == "transaction":
                continue
            if scope and not (c.subject in scope and held in scope):
                continue
            sub = ""
            if blocker:
                what = c.predicate.replace("_unresolved", "").replace(
                    "_", " ").upper()
                label, sub, kind = (what, "UNRESOLVED", "blocker")
            elif "ultimate_controlling" in c.predicate:
                label, sub, kind = ("ultimate controlling party",
                                    "per FY2025 AR", "solid")
            elif "beneficial_interest" in c.predicate:
                label, sub, kind = ("beneficial interest",
                                    "% unresolved", "acknowledged")
            elif isinstance(c.object, dict) and (
                    c.object.get("pct") or c.object.get("shares")):
                bits = [b for b in (
                    c.object.get("pct"),
                    _abbr_shares(c.object["shares"])
                    if c.object.get("shares") else None) if b]
                label = " · ".join(bits)
                if c.object.get("as_of"):
                    sub = f"as of {c.object['as_of']}"
                kind = "solid"
            else:
                label = c.predicate.replace("registry_", "").replace(
                    "_", " ")
                kind = ("tentative" if "heritage" in c.predicate
                        else "solid")
            note = ""
            for ev in events:
                o = ev.object if isinstance(ev.object, dict) else {}
                if o.get("holder") == c.subject and \
                        o.get("company") == held:
                    note = "↓ " + str(o.get("delta", "changed")).replace(
                        "-376,125,000 shares", "−376.1M sh").replace(
                        "-10.70pp / ", "10.70pp since 2024 · ")
            edges.append({"a": c.subject, "b": held, "label": label,
                          "sub": sub, "note": note, "kind": kind})
    return edges


EDGE_STYLE = {
    "solid": ('style="stroke:var(--muted)"', "var(--ink)"),
    "acknowledged": ('style="stroke:var(--muted)" '
                     'stroke-dasharray="7 4"', "var(--muted)"),
    "tentative": ('style="stroke:var(--muted)" stroke-dasharray="4 4"',
                  "var(--muted)"),
    "blocker": ('style="stroke:var(--burgundy)" stroke-dasharray="5 4"',
                "var(--burgundy)"),
}


def graph_svg(led, edges) -> str:
    """Boxes and lines. Nothing fancy. Answers: what owns what now?"""
    if not edges:
        return '<p class="muted">No current ownership edges.</p>'
    nodes = sorted({e["a"] for e in edges} | {e["b"] for e in edges})
    holders = {e["a"] for e in edges}
    helds = {e["b"] for e in edges}

    def row(n):
        t = led.entities[n].type
        if t in ("family", "branch", "person"):
            return 0
        if n in holders and n in helds:
            return 1
        return 2 if n in helds else 1

    rows = {}
    for n in nodes:
        rows.setdefault(row(n), []).append(n)
    bw, bh, gx, gy, pad = 190, 40, 30, 104, 20
    pos = {}
    width = max((len(v) * (bw + gx)) for v in rows.values()) + pad * 2
    for r, ns in sorted(rows.items()):
        total = len(ns) * (bw + gx) - gx
        x0 = (width - total) / 2
        for i, n in enumerate(sorted(ns)):
            pos[n] = (x0 + i * (bw + gx), pad + r * (bh + gy))
    height = pad * 2 + (max(rows) + 1) * (bh + gy) - gy
    out = [f'<svg viewBox="0 0 {width:.0f} {height:.0f}" '
           f'style="max-width:100%;font:12px Inter,sans-serif">']
    for e in edges:
        (x1, y1), (x2, y2) = pos[e["a"]], pos[e["b"]]
        x1 += bw / 2; y1 += bh; x2 += bw / 2
        if pos[e["a"]][1] == pos[e["b"]][1]:
            y1 = pos[e["a"]][1] + bh / 2; y2 = y1
            x1 = pos[e["a"]][0] + bw; x2 = pos[e["b"]][0]
        line_style, text_fill = EDGE_STYLE[e["kind"]]
        out.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" '
                   f'y2="{y2:.0f}" {line_style}/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        lines = [(e["label"], text_fill, -6)]
        if e["sub"]:
            lines.append((e["sub"], "var(--muted)", 6))
        if e["note"]:
            lines.append((e["note"], "var(--burgundy)",
                          18 if e["sub"] else 6))
        for txt, fill, dy in lines:
            out.append(f'<text x="{mx:.0f}" y="{my+dy:.0f}" '
                       f'text-anchor="middle" style="fill:{fill};'
                       f'font-size:10px">{esc(txt)}</text>')
    for n, (x, y) in pos.items():
        name = led.entities[n].name
        name = name if len(name) <= 26 else name[:25] + "…"
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{bw}" '
                   f'height="{bh}" rx="3" style="fill:var(--panel);'
                   f'stroke:var(--rule)"/>')
        out.append(f'<text x="{x+bw/2:.0f}" y="{y+bh/2+4:.0f}" '
                   f'text-anchor="middle" style="fill:var(--ink)">'
                   f'{esc(name)}</text>')
    out.append("</svg>")
    return "".join(out)


def ownership_edges(led, scope=None):
    """Back-compat alias for older callers."""
    return ownership_view(led, scope)


def connected(led, root, hops=2):
    """Entity ids within N claim-hops of root."""
    seen = {root}
    frontier = {root}
    for _ in range(hops):
        nxt = set()
        for c in led.claims.values():
            ends = [c.subject] + _entity_refs(led, c.object)
            if any(e in frontier for e in ends):
                nxt.update(ends)
        nxt -= seen
        seen |= nxt
        frontier = nxt
    return seen


def dossier(led, fam) -> str:
    scope = connected(led, fam.id)
    claims = sorted([c for c in led.claims.values()
                     if c.subject in scope or
                     set(_entity_refs(led, c.object)) & scope],
                    key=lambda c: c.id)
    by = {"APPROVED": [], "PENDING": [], "REJECTED": []}
    for c in claims:
        if c.status == "APPROVED":
            by["APPROVED"].append(c)
        elif c.status in ("PROPOSED", "LEAD"):
            by["PENDING"].append(c)
        elif c.status == "REJECTED":
            by["REJECTED"].append(c)
    srcs = sorted({s for c in claims for s in c.sources})
    companies = sorted([e for e in scope
                        if led.entities[e].type == "company"])
    dated = sorted([c for c in claims if c.valid_from],
                   key=lambda c: (str(c.valid_from), c.id))
    tl = "".join(
        f'<dt>{esc(c.valid_from)}</dt>'
        f'<dd><a href="#c-{esc(c.id)}">{esc(c.id)}</a> — '
        f'{link_entity(led, c.subject)} {esc(c.predicate)} '
        f'{render_object(led, c.object)}</dd>'
        for c in dated) or "<dt>—</dt><dd class='muted'>no dated " \
                           "claims yet</dd>"
    rows = [
        ("Sources", " · ".join(f'<a href="#s-{esc(s)}">{esc(s)}</a>'
                               for s in srcs) or
         '<span class="muted">—</span>'),
        ("Claims", " · ".join(
            f'{k.title()}: <b>{len(v)}</b>' for k, v in by.items())),
        ("Companies", " · ".join(link_entity(led, c)
                                 for c in companies) or
         '<span class="muted">—</span>'),
    ]
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    svg = graph_svg(led, ownership_edges(led, scope=scope))
    return (f'<div class="card" id="d-{esc(fam.id)}">'
            f'<div class="cardhead"><b>{esc(fam.name)}</b>'
            f'<span class="muted">analyst dossier</span></div>'
            f'<dl>{dl}</dl>'
            f'<h3 style="font:600 10.5px/1 Inter;letter-spacing:.14em;'
            f'text-transform:uppercase;color:var(--muted);'
            f'margin:16px 0 8px">Graph</h3>{svg}'
            f'<h3 style="font:600 10.5px/1 Inter;letter-spacing:.14em;'
            f'text-transform:uppercase;color:var(--muted);'
            f'margin:16px 0 8px">Timeline</h3><dl>{tl}</dl></div>')


def research_queue(led) -> str:
    """Materiality-ordered blockers: impact x confidence gap x ease.
    v1 uses explicit rules; scores get quantitative as valuation
    coverage grows."""
    items = []
    block_value = ""
    try:
        from valuation import decompose_family
        fams = [e.id for e in led.entities.values()
                if e.type == "family"]
        for f in fams:
            for d in decompose_family(led, f):
                if "error" not in d and d.get("value_usd"):
                    block_value = (f"gates ≈USD {d['value_usd']/1e6:,.0f}M "
                                   f"(mark-to-model)")
    except Exception:
        pass
    controllers = {c.subject for c in led.claims.values()
                   if "ultimate_controlling" in c.predicate
                   and c.status in ("PROPOSED", "APPROVED")}
    for c in led.claims.values():
        if c.status in ("SUPERSEDED", "RETRACTED", "REJECTED"):
            continue
        f = freshness(c, TODAY)
        if c.predicate.endswith("_unresolved"):
            subj = led.entities.get(c.subject)
            if subj and subj.id in controllers:
                items.append(("H", f"{esc(c.id)} — "
                              f"{esc(c.predicate.replace('_', ' '))}: "
                              f"{link_entity(led, c.subject)}",
                              "Ultimate controlling party of a tracked "
                              "listed company — the top of the chain; "
                              f"{esc(block_value)}" if block_value else
                              "Ultimate controlling party — top of the "
                              "chain",
                              "Cayman General Registry + Jamaican "
                              "disclosures + press"))
            elif subj and subj.type == "family":
                items.append(("H", f"{esc(c.id)} — beneficial ownership "
                              f"of {link_entity(led, c.object) if isinstance(c.object, str) else '?'}",
                              f"Primary blocker; {esc(block_value)}"
                              if block_value else "Primary blocker",
                              "COJ reverse search + BO registry"))
            else:
                items.append(("M", f"{esc(c.id)} — who is behind "
                              f"{link_entity(led, c.subject)}?",
                              "Unidentified holder of a tracked listed "
                              "company", "Registry record (COJ/CAIPO)"))
        elif c.predicate == "member_of" and c.status == "LEAD":
            items.append(("M", f"{esc(c.id)} — kinship: "
                          f"{link_entity(led, c.subject)}",
                          "Quick win: cheap to resolve, unlocks family "
                          "membership edges", "RGD / AR bios / on-record"))
        elif "acquirer" in c.predicate and c.status == "LEAD":
            items.append(("L", f"{esc(c.id)} — "
                          f"{link_entity(led, c.subject)} stake in "
                          f"{render_object(led, c.object)}",
                          "Confirm legal name + materiality",
                          "COJ + press retrieval"))
        elif c.predicate in ("reported_price", "reported_market_stats") \
                and f == "stale" and c.status != "LEAD":
            items.append(("M", f"{esc(c.id)} — refresh "
                          f"{esc(c.predicate.replace('_', ' '))} for "
                          f"{link_entity(led, c.subject)}",
                          "Stale market input gates a live mark",
                          "JSE close / current quote"))
    for s in led.sources.values():
        if not s.preserved and "archival target" in s.notes.lower():
            items.append(("H", f'<a href="#s-{esc(s.id)}">{esc(s.id)}'
                          f"</a> — archive: {esc(s.description[:70])}",
                          "Named archival target — one document may "
                          "collapse several unresolved claims at once "
                          "(listing documents especially: issuers must "
                          "explain pre-IPO ownership at the listing "
                          "event)",
                          "Download + archive.add() → evidence paths "
                          "complete"))
    order = {"H": 0, "M": 1, "L": 2}
    items.sort(key=lambda t: order[t[0]])
    if not items:
        return '<p class="muted">Queue empty.</p>'
    rows = "".join(
        f'<tr><td><span class="pill" style="color:'
        f'{"var(--burgundy)" if p == "H" else "var(--navy)" if p == "M" else "var(--muted)"}">'
        f'{p}</span></td><td>{item}</td><td>{why}</td><td>{route}</td>'
        f"</tr>" for p, item, why, route in items)
    return ('<div class="tablewrap"><table><tr><th></th><th>Item</th>'
            '<th>Why it matters</th><th>Route</th></tr>' + rows +
            "</table></div>")


def main() -> None:
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "explorer.html"
    led = Ledger(data_dir)

    approved = led.query(status="APPROVED")
    research = [c for c in led.claims.values()
                if c.status in ("PROPOSED", "LEAD")]
    history = [c for c in led.claims.values()
               if c.status in ("SUPERSEDED", "RETRACTED", "REJECTED")]

    parts = [f"<title>Claim Explorer</title><style>{CSS}</style>"]
    parts.append(
        '<header><span class="wordmark">Claim Explorer</span>'
        f'<span class="stat">Verified graph <b>{len(approved)}</b></span>'
        f'<span class="stat">Research layer <b>{len(research)}</b></span>'
        f'<span class="stat">History <b>{len(history)}</b></span>'
        f'<span class="stat">Entities <b>{len(led.entities)}</b></span>'
        f'<span class="stat">Sources <b>{len(led.sources)}</b></span>'
        '</header><main>')

    parts.append("<h2>Entities</h2><div class='chips'>")
    for e in sorted(led.entities.values(), key=lambda e: e.name):
        n = sum(1 for c in led.claims.values()
                if c.subject == e.id or c.object == e.id)
        parts.append(f'<a class="chip" href="#e-{esc(e.id)}">{esc(e.name)} '
                     f'<small>{esc(e.type)} · {n}</small></a>')
    parts.append("</div>")

    parts.append("<h2>Research queue (materiality-ordered)</h2>")
    parts.append(research_queue(led))

    parts.append("<h2>Family dossiers</h2>")
    fams = [e for e in led.entities.values() if e.type == "family"]
    for fam in sorted(fams, key=lambda e: e.name):
        parts.append(dossier(led, fam))

    for title, group in (("Verified graph (approved claims)", approved),
                         ("Research layer (proposed & leads)", research),
                         ("History (superseded & retracted)", history)):
        parts.append(f"<h2>{esc(title)}</h2>")
        if not group:
            parts.append('<p class="muted">Empty' + (
                " — correctly so: nothing enters the verified graph "
                "without analyst approval against a complete evidence "
                "path.</p>" if "Verified" in title else ".</p>"))
        for c in sorted(group, key=lambda c: c.id):
            parts.append(claim_card(led, c))

    parts.append("<h2>Entity detail</h2>")
    for e in sorted(led.entities.values(), key=lambda e: e.name):
        about = sorted([c for c in led.claims.values()
                        if c.subject == e.id or c.object == e.id],
                       key=lambda c: c.id)
        links = " · ".join(f'<a href="#c-{esc(c.id)}">{esc(c.id)}</a>'
                           for c in about) or '<span class="muted">—</span>'
        meta = " · ".join(filter(None, [esc(e.type),
                                        esc(e.jurisdiction or ""),
                                        esc(e.status or "")]))
        notes = f"<dt>Notes</dt><dd>{esc(e.notes)}</dd>" if e.notes else ""
        parts.append(
            f'<div class="card" id="e-{esc(e.id)}"><div class="cardhead">'
            f'<b>{esc(e.name)}</b><span class="muted">{meta}</span></div>'
            f'<dl><dt>Claims</dt><dd>{links}</dd>{notes}</dl></div>')

    parts.append("<h2>Extractions</h2>")
    for x in sorted(led.extractions.values(), key=lambda x: x.id):
        cites = " · ".join(f'<a href="#c-{esc(c.id)}">{esc(c.id)}</a>'
                           for c in sorted(led.claims.values(),
                                           key=lambda c: c.id)
                           if x.id in c.extractions) or \
            '<span class="muted">—</span>'
        rows = [("Source", f'<a href="#s-{esc(x.source_id)}">'
                 f'{esc(x.source_id)}</a>'),
                ("Passage", esc(x.passage)),
                ("Locator", esc(x.locator) or
                 '<span class="muted">—</span>'),
                ("Method", esc(x.method)),
                ("Analyst", esc(x.analyst) or
                 '<span class="muted">—</span>'),
                ("Supports", cites)]
        if x.notes:
            rows.append(("Notes", esc(x.notes)))
        dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
        parts.append(f'<div class="card" id="x-{esc(x.id)}">'
                     f'<div class="cardhead"><span class="cid">'
                     f'{esc(x.id)}</span></div><dl>{dl}</dl></div>')

    parts.append("<h2>Sources</h2>")
    for s in sorted(led.sources.values(), key=lambda s: s.id):
        cites = " · ".join(f'<a href="#c-{esc(c.id)}">{esc(c.id)}</a>'
                           for c in sorted(led.claims.values(),
                                           key=lambda c: c.id)
                           if s.id in c.sources) or \
            '<span class="muted">—</span>'
        pres = ('<span class="path-ok">preserved · ' +
                esc(s.archive_ref) + '</span>' if s.preserved else
                '<span class="path-gap">not preserved</span>')
        url = (f'<a href="{esc(s.url_or_registry_id)}" target="_blank" '
               f'rel="noopener">{esc(s.url_or_registry_id)}</a>'
               if s.url_or_registry_id else '<span class="muted">—</span>')
        rows = [("Description", esc(s.description)),
                ("Tier", esc(s.tier)),
                ("Retrieved", esc(s.retrieval_date)),
                ("Location", url),
                ("Passage", esc(s.passage) or '<span class="muted">—</span>'),
                ("Access", esc(s.access)),
                ("Preservation", pres),
                ("Analyst", esc(s.analyst) or '<span class="muted">—</span>'),
                ("Cited by", cites)]
        if s.notes:
            rows.append(("Notes", esc(s.notes)))
        dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
        parts.append(f'<div class="card" id="s-{esc(s.id)}">'
                     f'<div class="cardhead"><span class="cid">{esc(s.id)}'
                     f'</span></div><dl>{dl}</dl></div>')

    parts.append("</main><footer>Internal tool — regenerate with "
                 "<code>python3 graph/explorer.py</code> after ledger "
                 "changes. The graph is the institution; everything else "
                 "is disposable.</footer>")

    with open(out_file, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out_file}: {len(approved)} approved, "
          f"{len(research)} research, {len(history)} history")


if __name__ == "__main__":
    main()
