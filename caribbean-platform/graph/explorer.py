"""Claim Explorer - renders the ledger as a browsable HTML page.

The graph shouldn't just exist; researchers browse it. Every claim card
shows the full record - subject, predicate, object, status, sources,
approval, supersession - plus the live evidence-path check, and links
click through: claim -> entity -> source -> citing claims.

Usage: python3 explorer.py [data_dir] [out_file]
Default: reads ./data, writes ./explorer.html
"""
from __future__ import annotations

import html
import sys

from schema import evidence_path_gaps
from store import Ledger

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


def claim_card(led, c) -> str:
    gaps = evidence_path_gaps(c, led.sources)
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
    ]
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


def main() -> None:
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "explorer.html"
    led = Ledger(data_dir)

    approved = led.query(status="APPROVED")
    research = [c for c in led.claims.values()
                if c.status in ("PROPOSED", "LEAD")]
    history = [c for c in led.claims.values()
               if c.status in ("SUPERSEDED", "RETRACTED")]

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
