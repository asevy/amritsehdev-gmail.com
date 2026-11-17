"""Test helpers: build model-style candidates against REAL stored page text,
so validation is exercised with crafted wrong claims, not only with the
deterministic extractor's own output."""

from __future__ import annotations

import re

from jmi import entities
from jmi.extract import Candidate, Location, norm_ws, paragraph_bounds
from jmi.validate import VContext


def version_of(ws, filename):
    return next(v for v in ws.store.find(ws.A, "document_versions") if v["filename"] == filename)


def vctx(ws, version):
    st, a = ws.store, ws.A
    doc = st.get(a, "documents", version["document_id"])
    pages = st.find(a, "pages", version_id=version["id"])
    tables = st.find(a, "doc_tables", version_id=version["id"])
    cid = doc["company_id"]
    projects = {p["id"]: p["name"] for p in entities.projects_of(st, a, cid)} if cid else {}
    return VContext(company_id=cid, company_projects=projects, aliases=entities.all_aliases(st, a),
                    reporting_currency=version["reporting_currency"],
                    doc_heading=doc["title"] + "\n" + (pages[0]["text"][:400] if pages else ""),
                    page_texts={p["page_no"]: p["text"] for p in pages},
                    table_cells={(t["table_index"], ri, ci): c for t in tables for ri, r in enumerate(t["rows"])
                                 for ci, c in enumerate(r)})


def passage_candidate(ws, version, page_no, quote_regex, metric, raw_value, **claims) -> Candidate:
    text = next(p["text"] for p in ws.store.find(ws.A, "pages", version_id=version["id"]) if p["page_no"] == page_no)
    m = re.search(quote_regex, text, re.S)
    assert m, f"quote not found: {quote_regex}"
    pa, pb = paragraph_bounds(text, *m.span())
    c = Candidate(metric_id=metric, quote=m.group(0), raw_value=raw_value, location=Location(page_no, m.start(), m.end()),
                  context=norm_ws(text[pa:pb]), rule_id="model")
    for k in ("fields", "qualifiers"):
        if k in claims:
            getattr(c, k).update(claims.pop(k))
    for k, v in claims.items():
        setattr(c, k, v)
    return c
