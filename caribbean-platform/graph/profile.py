"""Generated family profile - the Phase 2 pipeline seed.

A family page is generated from the graph, never manually written:
narrative slot -> fortune block -> ownership graph -> companies ->
properties -> timeline -> methodology & evidence. By default only
APPROVED claims render (the public rule); --include-research produces an
internal preview with the research layer clearly labeled.

The first-milestone test: one complete family, raw documents -> approved
claims -> this page, with zero manual copy-paste.

Usage: python3 profile.py <family_entity_id> <out.html>
                          [--include-research]
"""
from __future__ import annotations

import datetime
import sys

from explorer import (CSS, connected, dossier, esc, graph_svg,
                      link_entity, ownership_edges, render_object)
from schema import evidence_path_gaps, publishable
from store import Ledger


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    include_research = "--include-research" in sys.argv
    fam_id, out_file = args[0], args[1]
    led = Ledger("data")
    fam = led.entities[fam_id]

    scope = connected(led, fam_id)
    all_claims = sorted(
        [c for c in led.claims.values()
         if (c.subject in scope) and
         c.status in (("APPROVED", "PROPOSED", "LEAD")
                      if include_research else ("APPROVED",))],
        key=lambda c: c.id)
    approved = [c for c in all_claims if c.status == "APPROVED"]

    edges = [e for e in ownership_edges(led, scope=scope)]
    companies = sorted([led.entities[e] for e in scope
                        if led.entities[e].type == "company"],
                       key=lambda e: e.name)
    props = sorted([led.entities[e] for e in scope
                    if led.entities[e].type in ("property", "asset")],
                   key=lambda e: e.name)
    dated = sorted([c for c in all_claims if c.valid_from],
                   key=lambda c: (str(c.valid_from), c.id))

    banner = ("" if not include_research else
              '<p style="border:1px solid var(--burgundy);'
              'color:var(--burgundy);padding:8px 12px;border-radius:4px;'
              'font-size:12.5px">INTERNAL PREVIEW — includes unapproved '
              'research-layer material. Not publishable.</p>')

    wealth = [c for c in approved if "wealth_estimate" in c.predicate]
    fortune = ("<dl>" + "".join(
        f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in
        (wealth[-1].object or {}).items()) + "</dl>"
        if wealth and isinstance(wealth[-1].object, dict) else
        '<p class="muted">No approved estimate. The graph does not yet '
        'support one — evidence pending, and the page says so rather '
        'than pretending.</p>')

    def sec(title, body):
        return f"<h2>{esc(title)}</h2>{body}"

    comp_list = ("<ul>" + "".join(
        f"<li>{link_entity(led, c.id)}"
        f'{" — <span class=muted>" + esc(c.notes) + "</span>" if c.notes else ""}</li>'
        for c in companies) + "</ul>") if companies else \
        '<p class="muted">None linked yet.</p>'
    prop_list = ("<ul>" + "".join(
        f"<li>{link_entity(led, p.id)}</li>" for p in props) + "</ul>") \
        if props else '<p class="muted">None linked yet.</p>'
    tl = ("<dl>" + "".join(
        f"<dt>{esc(c.valid_from)}</dt><dd>{link_entity(led, c.subject)} "
        f"{esc(c.predicate.replace('_', ' '))} "
        f"{render_object(led, c.object)}"
        f"{' <span class=muted>[' + esc(c.status) + ']</span>' if c.status != 'APPROVED' else ''}"
        f"</dd>" for c in dated) + "</dl>") if dated else \
        '<p class="muted">No dated claims yet.</p>'

    meth_rows = []
    for c in all_claims:
        gaps = evidence_path_gaps(c, led.sources)
        pub = publishable(c, led.sources)
        meth_rows.append(
            f"<tr><td>{esc(c.id)}</td><td>{esc(c.status)}</td>"
            f"<td>{esc(c.predicate)}</td>"
            f"<td>{', '.join(esc(s) for s in c.sources) or '—'}</td>"
            f"<td>{'complete' if not gaps else 'incomplete'}</td>"
            f"<td>{'yes' if pub else 'no'}</td></tr>")
    meth = ('<div style="overflow-x:auto"><table style="width:100%;'
            'border-collapse:collapse;font-size:12.5px">'
            '<tr><th>Claim</th><th>Status</th><th>Predicate</th>'
            '<th>Sources</th><th>Evidence path</th><th>Publishable</th>'
            '</tr>' + "".join(meth_rows) + "</table></div>"
            ) if meth_rows else '<p class="muted">No claims in scope.</p>'

    meta = " · ".join(filter(None, [
        (fam.jurisdiction or "").upper(), "FAMILY"]))
    stamp = datetime.date.today().isoformat()
    html = f"""<title>{esc(fam.name)}</title><style>{CSS}
h1{{font:600 34px/1.15 Georgia,serif;margin:.2em 0 .1em}}
.meta{{font:500 11px/1 Inter;letter-spacing:.16em;color:var(--muted)}}
th{{text-align:left;color:var(--muted);font:600 10.5px/1.6 Inter;
letter-spacing:.1em;text-transform:uppercase;border-bottom:1px solid
var(--rule);padding:6px 8px}}
td{{border-bottom:1px solid var(--rule);padding:6px 8px;
vertical-align:top}}</style>
<main>
{banner}
<p class="meta">{esc(meta)}</p>
<h1>{esc(fam.name)}</h1>
<p class="muted"><em>[Narrative — written by a journalist; the database
supplies the facts. {esc(fam.notes)}]</em></p>
{sec("The fortune", fortune)}
{sec("Ownership graph", graph_svg(led, edges))}
{sec("Companies", comp_list)}
{sec("Properties", prop_list)}
{sec("Timeline", tl)}
{sec("Methodology & evidence", meth)}
</main>
<footer>Generated from the graph on {stamp} — zero manual copy-paste.
Regenerate: <code>python3 graph/profile.py {esc(fam_id)} …</code>
</footer>"""
    with open(out_file, "w") as f:
        f.write(html)
    print(f"wrote {out_file}: {len(approved)} approved / "
          f"{len(all_claims)} rendered claims, {len(companies)} "
          f"companies, {len(edges)} edges")


if __name__ == "__main__":
    main()
