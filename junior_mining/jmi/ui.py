"""Server-rendered HTML for the eight working screens (brief §13).

No JavaScript: every action is an ordinary form POST carrying the session's
CSRF token, so the Content-Security-Policy can forbid scripts entirely.
Status is written in words, not colours; there are no badges, stars, traffic
lights or default rankings. Missing information is shown as missing, with
what would establish it. Quoted source text is set in <blockquote>/<q> so it
is visibly the document speaking, not the application.
"""

from __future__ import annotations

import html
import json
from decimal import Decimal
from urllib.parse import quote as urlq

from . import definitions as D
from .quantities import fmt

CSS = """
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif;color:#15191c;background:#f6f7f7}
header{background:#fff;border-bottom:1px solid #d6dadc;padding:10px 22px;display:flex;gap:18px;align-items:baseline;flex-wrap:wrap}
header .mark{font-weight:600;letter-spacing:.5px}header nav a{margin-right:12px}header .who{margin-left:auto;color:#5b6368;font-size:12.5px}
main{padding:18px 22px;max-width:1400px}a{color:#0b5d6b}h1{font-size:20px;margin:6px 0 12px}h2{font-size:16px;margin:22px 0 8px}h3{font-size:14px;margin:16px 0 6px}
table{border-collapse:collapse;width:100%;background:#fff;margin:6px 0 14px}th,td{border:1px solid #d6dadc;padding:5px 8px;text-align:left;vertical-align:top}
th{background:#eef0f1;font-weight:600}td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.note{color:#4d5559;font-size:12.5px}.missing{font-style:italic;color:#4d5559}.withheld{font-style:italic}
.banner{border:1px solid #15191c;background:#fff;padding:8px 12px;margin:8px 0 14px;font-weight:600}
.synthetic{border:1px dashed #15191c;padding:6px 10px;margin:8px 0;background:#fff;font-size:12.5px}
blockquote,q.src{background:#fff;border-left:3px solid #9aa3a7;margin:6px 0;padding:6px 10px;white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace;font-size:12.5px;display:block}
pre.page{background:#fff;border:1px solid #d6dadc;padding:10px;white-space:pre-wrap;font-size:12.5px}mark{background:#ffe9a8;outline:1px solid #8a6d00}
form.inline{display:inline}form{margin:6px 0}label{display:block;font-size:12.5px;color:#4d5559;margin-top:6px}
input,select,textarea{font:inherit;padding:4px 6px;border:1px solid #b8bfc2;border-radius:3px;background:#fff}textarea{width:100%;min-height:60px}
button{font:inherit;padding:4px 10px;border:1px solid #15191c;background:#fff;border-radius:3px;cursor:pointer}
details{background:#fff;border:1px solid #d6dadc;padding:6px 10px;margin:8px 0}summary{cursor:pointer;font-weight:600}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}.sub{margin:4px 0 12px}.sub a{margin-right:12px}
.scroll{overflow-x:auto}table.wide td,table.wide th{min-width:150px}table.wide td:first-child{min-width:220px}
th a{text-decoration:none}
"""


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def page(title: str, body: str, actor=None, company: dict | None = None, notice: str | None = None) -> bytes:
    nav = ""
    if actor:
        links = [("/", "Coverage"), ("/review", "Review queue"), ("/discrepancies", "Discrepancies"),
                 ("/inbox", "Change inbox"), ("/portfolio", "Portfolio"), ("/definitions", "Definitions")]
        if actor.can("admin"):
            links += [("/admin/audit", "Audit"), ("/admin/usage", "Usage"), ("/admin/users", "Users")]
        nav = "<nav>" + "".join(f'<a href="{h}">{esc(t)}</a>' for h, t in links) + "</nav>"
        nav += (f'<span class="who">{esc(actor.user_id)} · {esc(actor.role)} · tenant {esc(actor.tenant_id)} · '
                f'<a href="/logout">sign out</a></span>')
    sub = ""
    if company:
        cid = company["id"]
        sub = ('<div class="sub">' + "".join(
            f'<a href="{h}">{t}</a>' for h, t in [
                (f"/company/{cid}", "Company & projects"), (f"/company/{cid}/documents", "Documents"),
                (f"/risks/{cid}", "Risks"), (f"/diligence/{cid}", "Diligence"), (f"/peers/{cid}", "Peers"),
                (f"/calcs/{cid}", "Calculations"), (f"/memos/{cid}", "Memos"), (f"/ask/{cid}", "Ask")]) + "</div>")
        if company.get("synthetic"):
            sub += '<div class="synthetic">SYNTHETIC development data — fictional issuer; not real issuer analysis.</div>'
    out = (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>{esc(title)}</title>"
           f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><style>{CSS}</style></head><body>"
           f"<header><span class=\"mark\">Junior Mining Intelligence</span>{nav}</header><main>"
           f"<h1>{esc(title)}</h1>{sub}" + (f'<div class="banner">{esc(notice)}</div>' if notice else "") +
           body + "</main></body></html>")
    return out.encode("utf-8")


def table(headers: list[str], rows: list[list[str]], empty: str = "Nothing recorded.", raw_headers: bool = False) -> str:
    """headers are escaped unless raw_headers=True (caller has already escaped them)."""
    if not rows:
        return f'<p class="missing">{esc(empty)}</p>'
    hs = "".join(f"<th>{h if raw_headers else esc(h)}</th>" for h in headers)
    return ('<div class="scroll"><table><thead><tr>' + hs + "</tr></thead><tbody>" +
            "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")


def form(action: str, inner: str, csrf: str, submit: str = "Save", next_url: str = "", inline: bool = False,
         multipart: bool = False) -> str:
    enc = ' enctype="multipart/form-data"' if multipart else ""
    cls = ' class="inline"' if inline else ""
    return (f'<form method="post" action="{esc(action)}"{enc}{cls}><input type="hidden" name="csrf" value="{esc(csrf)}">'
            f'<input type="hidden" name="_next" value="{esc(next_url)}">{inner}<button>{esc(submit)}</button></form>')


def inp(name, label, value="", type="text", required=False, size=30) -> str:
    return (f'<label>{esc(label)}<br><input name="{esc(name)}" type="{type}" value="{esc(value)}" size="{size}"'
            + (" required" if required else "") + "></label>")


def hid(name, value) -> str:
    return f'<input type="hidden" name="{esc(name)}" value="{esc(value)}">'


def sel(name, label, options, selected=None) -> str:
    return (f'<label>{esc(label)}<br><select name="{esc(name)}">' + "".join(
        f'<option value="{esc(v)}"' + (" selected" if v == selected else "") + f">{esc(t)}</option>"
        for v, t in options) + "</select></label>")


def ta(name, label, value="") -> str:
    return f'<label>{esc(label)}<br><textarea name="{esc(name)}">{esc(value)}</textarea></label>'


def missing(text="Not found in documents reviewed") -> str:
    return f'<span class="missing">{esc(text)}</span>'


def state_word(state: str) -> str:
    return esc(D.WORKFLOW_STATES.get(state, state).split(" —")[0])


def fact_value(f: dict) -> str:
    d = D.metric(f["metric_id"])
    if f["value_kind"] == "enum":
        return esc(D.PERMIT_STATUSES.get(f["normalized_value"], f["qualifiers"].get("label", f["normalized_value"])))
    if f["normalized_value"] is None:
        return missing("value not readable — see checks")
    v = Decimal(f["normalized_value"])
    cur = f["currency"] + " " if f["currency"] and d.dimension in ("money", "price_per_metal") else ""
    unit = "" if d.dimension == "money" else (f" {f['unit']}" if f["unit"] and not d.display_suffix else "")
    return esc(f"{cur}{fmt(v, d.display_decimals, d.display_divisor)}{d.display_suffix}{unit}")


def fact_date(f: dict) -> str:
    if f["as_of_date"]:
        return esc(f"as at {f['as_of_date']}")
    if f["effective_date"]:
        return esc(f"effective {f['effective_date']}")
    if f["period_end"]:
        return esc(f"{f['period_start'] or '?'} to {f['period_end']}")
    return missing("date not stated")


def src_link(f: dict) -> str:
    if not f.get("version_id"):
        return missing("no source")
    return f'<a href="/doc/{esc(f["version_id"])}?loc={esc(f["location_id"])}#loc">source</a>'


def qualifiers_text(f: dict) -> str:
    parts = []
    if f["resource_category"]:
        parts.append(D.CATEGORY_LABELS[f["resource_category"]])
    if f["scope_basis"]:
        parts.append(f"{f['scope_basis']} basis")
    if f["reporting_basis"]:
        parts.append(f"{f['reporting_basis']} of reserves")
    if f["study_type"]:
        parts.append(f["study_type"].upper())
    if f["tax_basis"]:
        parts.append(f["tax_basis"].replace("_", "-"))
    if f["discount_rate"]:
        parts.append(f"{f['discount_rate']}% discount")
    if f["estimate_status"] == "historical":
        parts.append("HISTORICAL (not current)")
    q = f["qualifiers"] or {}
    for k in ("zone", "hole_id", "interval", "permit", "listing", "window", "exercise_price", "expiry", "price_case",
              "test_type", "bound", "true_width_status"):
        if q.get(k):
            parts.append(f"{k.replace('_', ' ')}: {q[k]}")
    return esc("; ".join(parts))


def fact_rows(facts: list[dict], with_actions: str = "") -> list[list[str]]:
    rows = []
    for f in facts:
        rows.append([esc(D.metric(f["metric_id"]).label), f'<span class="num">{fact_value(f)}</span>',
                     qualifiers_text(f), fact_date(f), esc(D.EVIDENCE_TYPES[f["evidence_type"]].split(" (")[0]),
                     state_word(f["workflow_state"]), src_link(f) + f' · <a href="/fact/{esc(f["id"])}">record</a>'])
    return rows


FACT_HEADERS = ["Metric", "Value", "Qualifiers", "Date", "Evidence type", "Checks completed", "Source"]


def coverage_block(cov: dict) -> str:
    docs = cov.get("documents_reviewed", [])
    s = (f'<p class="note">Analysis time {esc(cov.get("analysis_time"))} · evidence cutoff '
         f'{esc(cov.get("evidence_cutoff") or "none")} · documents reviewed {len(docs)}')
    if cov.get("ingestion_failed"):
        s += f" · <b>ingestion failed: {len(cov['ingestion_failed'])}</b>"
    if cov.get("unreadable_pages"):
        s += f" · <b>unreadable pages not reviewed</b>"
    if cov.get("mirrors_not_counted"):
        s += f" · mirrored releases not counted: {len(cov['mirrors_not_counted'])}"
    return s + "</p>"


def jsonblock(obj) -> str:
    return f"<pre class=\"page\">{esc(json.dumps(obj, indent=1, default=str))}</pre>"


def calc_rows(calcs: list[dict]) -> list[list[str]]:
    rows = []
    for c in calcs:
        val = esc(c["display_value"]) if c["status"] == "computed" else \
            f'<span class="withheld">Withheld — {esc("; ".join(c["missing"]))}</span>'
        if c["stale"]:
            val += f'<br><b>STALE:</b> {esc(c["stale_reason"])}'
        inputs = "<br>".join(
            esc(f"{i['name']} = {i['value']} {i.get('unit') or ''} ({i['kind']}{(' ' + i['ref_id']) if i.get('ref_id') else ''}"
                f"{(', ' + i['date']) if i.get('date') else ''})") +
            (f' <a href="/fact/{esc(i["ref_id"])}">fact</a>' if i["kind"] == "fact" and i.get("ref_id") else "")
            for i in c["inputs"])
        notes = "<br>".join(esc(w) for w in (c["warnings"] + c["caveats"]))
        rows.append([esc(c["label"]) + f'<br><span class="note">{esc(c["formula_id"])} v{c["formula_version"]} · '
                     f'<a href="/calc/{esc(c["id"])}">record</a></span>', val, inputs or missing("none"), notes])
    return rows
