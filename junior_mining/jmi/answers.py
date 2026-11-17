"""Constrained question answering (brief §7 "Retrieval and answers",
"Withholding and publication").

Answers are assembled from stored, cited facts within an explicit scope
(tenant, company, optional project and date). No model writes free text here,
and nothing is filled from general knowledge or the open web. When the
records cannot answer, the reply says so, lists the coverage it searched, and
suggests the document that would answer it. "Not found in documents reviewed"
is used where that is all the search establishes; it is never phrased as a
confirmed absence.

Retrieval relevance (FTS5 bm25) orders passages internally and is never shown.
"""

from __future__ import annotations

import re

from . import config, entities, facts as F, ingest
from . import definitions as D
from .auth import Actor
from .memo import fact_claim_text
from .store import Store

REFUSALS = [
    (re.compile(r"\b(should|would you|do you recommend|is it a good)\b[^?]*\b(buy|sell|invest|hold|short)\b", re.I),
     "This system does not make buy, sell or hold recommendations."),
    (re.compile(r"\b(probabilit\w*|likelihood|chance|odds|how likely)\b", re.I),
     "This system does not estimate probabilities of success or of any outcome."),
    (re.compile(r"\b(score|rating|rank|ranking|stars?|investment[- ]quality|letter grade|confidence)\b", re.I),
     "This system does not produce scores, ratings, rankings or confidence percentages."),
    (re.compile(r"\bprice target\b|\bfair value\b|\bwhat is it worth\b", re.I),
     "This system does not produce price targets. Scenario calculations with stated assumptions are available "
     "on the calculations page."),
    (re.compile(r"\b(fraud|scam|crook|dishonest|lying|honest)\b", re.I),
     "This system does not label fraud or misconduct, or judge honesty. Documented discrepancies and open "
     "questions are listed with attribution in the discrepancy workspace and risk register."),
    (re.compile(r"\bwill\b[^?]*\b(succeed|reach production|be built|go up|rise|outperform)\b", re.I),
     "This system does not forecast outcomes. It reports what documents state, attributed, with dates."),
]

INTENTS = [
    (r"(?<!un)restricted cash", ["cash_restricted"]),     # "unrestricted cash" is the other metric
    (r"\bcash\b|liquidity position", ["cash_unrestricted"]),
    (r"\bdebt\b|borrowing|loan", ["total_debt"]),
    (r"\bwarrants?\b", ["warrants_outstanding"]),
    (r"\boptions?\b", ["options_outstanding"]),
    (r"shares? outstanding|share count|basic shares", ["shares_outstanding_basic"]),
    (r"\bnpv\b|net present value", ["npv"]),
    (r"\birr\b", ["irr"]),
    (r"capex|capital cost|initial capital", ["initial_capex"]),
    (r"\baisc\b|all-in sustaining", ["aisc"]),
    (r"gold price|price assumption", ["commodity_price_assumption"]),
    (r"recover", ["met_test_recovery", "plant_recovery_assumption"]),
    (r"\breserves?\b", ["reserve_contained_metal"]),
    (r"historical estimate", ["historical_estimate_contained_metal"]),
    (r"resources?|ounces|contained", ["resource_contained_metal"]),
    (r"permit|permitting|authori[sz]ation|\beis\b|environmental approval", ["permit_status"]),
    (r"ownership|interest in", ["ownership_interest"]),
    (r"true width", ["true_width"]),
    (r"intercept|drill", ["drill_intercept_length", "drill_intercept_grade"]),
    (r"going concern|material uncertainty", ["disclosure_signal"]),
    (r"share price|closing price|\bprice\b", ["share_price"]),
    (r"volume|\badv\b|liquidity", ["average_daily_volume"]),
    (r"tonnage|tonnes", ["resource_tonnage"]),
    (r"\bgrade\b", ["resource_grade"]),
]


def _coverage_text(cov: dict) -> list[str]:
    docs = [f"{d['title']} ({d['publication_date'] or 'undated'})" for d in cov["documents_reviewed"]]
    out = [f"Documents reviewed ({len(docs)}): " + ("; ".join(docs) if docs else "none")]
    if cov["ingestion_failed"]:
        out.append("Not reviewed — ingestion failed: " + "; ".join(x["title"] for x in cov["ingestion_failed"]))
    if cov["unreadable_pages"]:
        out.append("Not reviewed — unreadable pages: " + "; ".join(
            f"{x['title']} p.{','.join(map(str, x['pages']))}" for x in cov["unreadable_pages"]))
    return out


def ask(store: Store, actor: Actor, company_id: str, question: str, project_id: str | None = None,
        as_of: str | None = None) -> dict:
    store.require(actor, "read")
    company = store.get(actor, "companies", company_id)
    if project_id:
        store.get(actor, "projects", project_id)
    q = (question or "").strip()
    store.audit(actor, "question_asked", company_id, q[:300])
    base = {"question": q, "scope": {"company": company["name"], "project_id": project_id, "as_of": as_of},
            "analysis_time": config.iso_now()}
    for rx, msg in REFUSALS:
        if rx.search(q):
            return {**base, "status": "declined", "answer": [], "message": msg}
    cov = ingest.coverage(store, actor, company_id)
    base["coverage"] = _coverage_text(cov)
    base["evidence_cutoff"] = cov["evidence_cutoff"]
    metrics, router, routed = [], "keyword rules", None
    from . import claude
    cfg = claude.get_config(store, actor)
    if cfg["enabled"] and cfg["route_questions"]:
        try:
            routed = claude.route_question(store, actor, q)
            router = f"Claude ({cfg['model']}) mapped the question to defined metrics; the answer below is assembled from stored records"
        except (claude.ClaudeUnavailable, claude.ClaudeRefused, claude.ClaudeBadOutput) as exc:
            router = f"keyword rules (Claude routing unavailable: {type(exc).__name__})"
    base["router"] = router
    if routed:
        oos = routed.get("out_of_scope")
        if oos:
            msg = {"recommendation": REFUSALS[0][1], "probability": REFUSALS[1][1], "score_or_rating": REFUSALS[2][1],
                   "price_target": REFUSALS[3][1], "misconduct_judgement": REFUSALS[4][1],
                   "forecast_of_outcome": REFUSALS[5][1]}.get(oos, "This question is outside what this system answers.")
            return {**base, "status": "declined", "answer": [], "message": msg}
        metrics = [m for m in routed.get("metric_ids", []) if m in D.METRICS]
    else:
        for pat, ms in INTENTS:
            if re.search(pat, q, re.I):
                metrics = ms
                break
    if not metrics:
        return {**base, **_passages(store, actor, company_id, q)}
    # Qualifiers named in the question: from Claude's routing when used, else from keywords.
    qual = {k: routed[k] for k in ("tax_basis", "resource_category") if routed and routed.get(k)}
    if not routed:
        if re.search(r"after[- ]tax", q, re.I):
            qual["tax_basis"] = "after_tax"
        elif re.search(r"pre[- ]tax", q, re.I):
            qual["tax_basis"] = "pre_tax"
        for pat, cat in ((r"measured\s*(?:&|and)\s*indicated|\bm&i\b", "measured_indicated"),
                         (r"\binferred\b", "inferred"), (r"\bindicated\b", "indicated"),
                         (r"\bmeasured\b", "measured"), (r"proven\s*(?:&|and)\s*probable|\bp&p\b", "proven_probable")):
            if re.search(pat, q, re.I):
                qual["resource_category"] = cat
                break
    lines, pending, missing = [], [], []
    for mid in metrics:
        rows = F.current(store, actor, company_id, mid, project_id)
        # a qualifier named in the question filters records that carry that qualifier
        rows = [f for f in rows if all(f.get(k) is None or f.get(k) == v for k, v in qual.items())]
        if as_of:
            rows = [f for f in rows if (f["as_of_date"] or f["effective_date"] or f["period_end"] or "") <= as_of]
        approved = [f for f in rows if f["workflow_state"] == "reviewer_approved"]
        others = [f for f in rows if f["workflow_state"] != "reviewer_approved"]
        for f in sorted(approved, key=lambda f: (f["as_of_date"] or f["effective_date"] or "", f["id"]), reverse=True):
            lines.append(_line(store, actor, f))
        for f in others:
            pending.append({**_line(store, actor, f),
                            "caveat": f"Not reviewer-approved (state: {D.WORKFLOW_STATES[f['workflow_state']].split(' —')[0]})."})
        if not rows:
            missing.append(mid)
    out = {**base, "metrics": [D.metric(m).label for m in metrics]}
    if "true_width" in metrics and not lines and not pending:
        intercepts = F.current(store, actor, company_id, "drill_intercept_length", project_id)
        notes = sorted({f["qualifiers"].get("true_width_status") for f in intercepts if f["qualifiers"].get("true_width_status")})
        return {**out, "status": "not_found", "answer": [],
                "message": "True width is not established in documents reviewed. Reported intercepts are down-hole "
                           "lengths" + (f"; true-width status stated: {'; '.join(notes)}." if notes else "."),
                "document_request": "Drill-hole orientation and true-width basis from the issuer's technical report."}
    if not lines and not pending:
        return {**out, "status": "not_found", "answer": [],
                "message": "Not found in documents reviewed. This does not establish that it does not exist.",
                "document_request": _request(missing)}
    return {**out, "status": "answered" if lines else "unapproved_only", "answer": lines,
            "unapproved": pending,
            "message": ("Answer assembled from reviewer-approved, cited facts." if lines else
                        "Only extracted, not-yet-approved records exist; shown with that caveat.")}


def _line(store, actor, f) -> dict:
    loc = store.get(actor, "source_locations", f["location_id"]) if f["location_id"] else None
    return {"fact_id": f["id"], "statement": fact_claim_text(store, actor, f),
            "evidence_type": D.EVIDENCE_TYPES[f["evidence_type"]], "state": f["workflow_state"],
            "quote": loc["quote"] if loc else None, "page": loc["page_no"] if loc else None,
            "location_id": f["location_id"], "version_id": f["version_id"]}


def _request(missing: list[str]) -> str:
    from .diligence import _doc_request
    return "; ".join(sorted({_doc_request(m) for m in missing})) or "Primary source document"


def _passages(store: Store, actor: Actor, company_id: str, q: str) -> dict:
    tenant = store.scope(actor)
    terms = [w for w in re.findall(r"[A-Za-z][A-Za-z-]{2,}", q) if w.lower() not in
             {"what", "which", "does", "the", "and", "for", "with", "there", "any", "have", "has", "about", "company",
              "project", "from", "this", "that", "are", "was", "were", "how", "many", "much", "when", "who"}]
    if not terms:
        return {"status": "not_found", "answer": [], "message": "No searchable terms in the question."}
    match = " OR ".join('"' + t.replace('"', "") + '"' for t in terms[:8])
    try:
        rows = store.db.all("SELECT version_id, page_no, snippet(passages_fts, 0, '[', ']', ' … ', 18) AS snip "
                            "FROM passages_fts WHERE passages_fts MATCH ? AND tenant_id=? AND company_id=? "
                            "ORDER BY bm25(passages_fts) LIMIT 5", (match, tenant, company_id))
    except Exception:
        rows = []
    if not rows:
        return {"status": "not_found", "answer": [],
                "message": "Not found in documents reviewed. No defined metric matches this question and no "
                           "passage contains its terms. This does not establish that it does not exist."}
    passages = []
    for r in rows:
        v = store.get(actor, "document_versions", r["version_id"])
        d = store.get(actor, "documents", v["document_id"])
        passages.append({"document": d["title"], "version_id": r["version_id"], "page": r["page_no"],
                         "excerpt": r["snip"], "mirror": bool(v["mirror_of_version_id"])})
    return {"status": "passages_only", "answer": [], "passages": passages,
            "message": "No defined metric answers this question, so no answer is stated. Passages containing its "
                       "terms are listed for reading; they are not an answer and have not been checked."}
