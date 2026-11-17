"""Thesis, claims and versioned investment memos (brief §7, §12, §13).

Every claim in a memo references fact / calculation / risk identifiers. The
validator checks the COMPLETE claim against what those records establish —
numbers, dates, category, permit status, attribution, forecast status and
required qualifiers — not merely that a number appears in a document. A
citation that does not support the full claim cannot be approved (brief §17
case 2). Claims that fail are withheld from the memo body and listed, with
reasons, as unresolved items.

During the institutional pilot, factual and interpretive claims require human
approval before a version can be labelled approved. Approval also requires
that every open risk in the register — with its contrary evidence — is in the
memo, that a counter-thesis exists, that nothing referenced is stale, and that
the approver is not the author. Approved versions are immutable: edits create
a new version; a later data correction flags the approved version as stale
without rewriting it.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal

from . import calc, config, facts as F, ingest, lineage
from . import definitions as D
from .auth import Actor
from .db import dumps
from .quantities import all_dates, fmt
from .store import AccessDenied, Invalid, NotFound, Store

SECTIONS = [("summary", "Summary"), ("thesis", "Thesis"), ("counter_thesis", "Counter-thesis"),
            ("material_facts", "Material facts (source-linked)"), ("valuation", "Calculations"),
            ("risks", "Risks and contrary evidence"), ("alternatives", "Alternatives considered"),
            ("diligence", "Specialist diligence outstanding")]

ATTRIBUTION_WORDS = re.compile(r"\b(reports?|reported|according to|states?|stated|discloses?|disclosed|"
                               r"estimates?|estimated|the (?:PEA|study|technical report|MD&A|release|presentation)|"
                               r"management|the company|issuer|per the)\b", re.I)
FORECAST_WORDS = re.compile(r"\b(estimates?|estimated|forecasts?|projected|PEA|pre-?feasibility|feasibility|study|"
                            r"targets?|expects?|assumes?|assumption)\b", re.I)


# ------------------------------------------------------------------ thesis
def create_thesis(store: Store, actor: Actor, company_id: str, title: str, thesis_text: str,
                  counter_thesis_text: str, assumptions: list[dict] | None = None) -> dict:
    if not counter_thesis_text.strip():
        raise Invalid("a thesis must be recorded with its counter-thesis")
    now = config.iso_now()
    with store.db.tx():
        t = store.insert(actor, "theses", {"company_id": company_id, "title": title, "created_by": actor.user_id,
                                           "created_at": now})
        tv = store.insert(actor, "thesis_versions", {"thesis_id": t["id"], "version_no": 1, "thesis_text": thesis_text,
                                                     "counter_thesis_text": counter_thesis_text,
                                                     "created_by": actor.user_id, "created_at": now})
        for a in assumptions or []:
            add_assumption(store, actor, tv["id"], company_id, a["text"], metric_ids=a.get("metric_ids", []),
                           fact_ids=a.get("fact_ids", []), calc_ids=a.get("calc_ids", []),
                           commitment_ids=a.get("commitment_ids", []), project_id=a.get("project_id"))
    return {"thesis": t, "version": tv}


def add_assumption(store, actor, thesis_version_id, company_id, text, *, metric_ids=(), fact_ids=(), calc_ids=(),
                   commitment_ids=(), project_id=None) -> dict:
    for f in fact_ids:
        store.get(actor, "facts", f)
    row = store.insert(actor, "thesis_assumptions", {
        "thesis_version_id": thesis_version_id, "text": text, "company_id": company_id, "project_id": project_id,
        "metric_ids": list(metric_ids), "fact_ids": list(fact_ids), "calc_ids": list(calc_ids),
        "commitment_ids": list(commitment_ids), "status": "holding", "status_reason": "",
        "updated_at": config.iso_now()})
    for f in fact_ids:
        lineage.link(store, actor, "fact", f, "thesis_assumption", row["id"])
    for c in calc_ids:
        lineage.link(store, actor, "calculation", c, "thesis_assumption", row["id"])
    return row


# ------------------------------------------------------------------ claim templates
def _loc_label(store, actor, f) -> str:
    if not f.get("version_id"):
        return "no source"
    v = store.get(actor, "document_versions", f["version_id"])
    d = store.get(actor, "documents", v["document_id"])
    loc = store.get(actor, "source_locations", f["location_id"]) if f.get("location_id") else None
    where = ""
    if loc:
        where = f", p.{loc['page_no']}" + (f" {loc['cell_ref']}" if loc.get("cell_ref") else "")
    return f"{d['title']}{where}"


def fact_claim_text(store: Store, actor: Actor, f: dict) -> str:
    d = D.metric(f["metric_id"])
    c = store.get(actor, "companies", f["company_id"])
    src = _loc_label(store, actor, f)
    if f["value_kind"] == "enum":
        val = D.PERMIT_STATUSES.get(f["normalized_value"], f["qualifiers"].get("label", f["normalized_value"]))
    elif f["normalized_value"] is None:
        val = "a value that could not be read"
    else:
        v = Decimal(f["normalized_value"])
        cur = f"{'C$' if f['currency'] == 'CAD' else 'US$' if f['currency'] == 'USD' else (f['currency'] or '')}"
        if d.dimension == "money":
            val = f"{cur}{fmt(v, d.display_decimals, d.display_divisor)}{d.display_suffix}"
        elif d.dimension == "price_per_metal":
            val = f"{cur}{fmt(v, 0)}/oz"
        elif d.dimension == "percent":
            val = f"{fmt(v, d.display_decimals)}%"
        elif d.dimension in ("mass", "metal"):
            val = f"{fmt(v, d.display_decimals, d.display_divisor)}{d.display_suffix}"
        elif d.dimension == "grade":
            val = f"{fmt(v, 2)} {f['unit']}"
        elif d.dimension == "length":
            val = f"{fmt(v, 1)} m"
        else:
            val = fmt(v, 0)
    quals = []
    if f["resource_category"]:
        quals.append(D.CATEGORY_LABELS[f["resource_category"]])
    if f["tax_basis"]:
        quals.append(f["tax_basis"].replace("_", "-"))
    if f["discount_rate"]:
        quals.append(f"{f['discount_rate']}% discount rate")
    if f["scope_basis"]:
        quals.append(f"{f['scope_basis']} basis")
    if f["qualifiers"].get("permit"):
        quals.append(f["qualifiers"]["permit"])
    if f["qualifiers"].get("hole_id"):
        quals.append(f"hole {f['qualifiers']['hole_id']}")
    date_s = (f"as at {f['as_of_date']}" if f["as_of_date"] else
              f"effective {f['effective_date']}" if f["effective_date"] else
              f"for the period ended {f['period_end']}" if f["period_end"] else "date not stated")
    who = {"issuer_management": f"{c['name']} reports", "qualified_person": f"{c['name']} reports (QP-prepared disclosure)",
           "market_data": "The uploaded market-data file reports", "regulator": "The official record states",
           "third_party": "A third party reports", "analyst": "Analyst entry:"}[f["attribution"]]
    study = f" The {f['study_type'].upper()} estimates this; it is a forecast, not an observed value." \
        if f["evidence_type"] == "forecast" and f["study_type"] else \
        (" This is a forecast, not an observed value." if f["evidence_type"] == "forecast" else "")
    extra = ""
    if f["metric_id"] == "drill_intercept_length":
        extra = f" This is a down-hole length; true width: {f['qualifiers'].get('true_width_status')}."
    return (f"{who} {d.label.lower()} of {val}" + (f" ({', '.join(quals)})" if quals else "") +
            f", {date_s} [{src}].{study}{extra}")


def _claim(kind, text, fact_ids=(), calc_ids=(), risk_ids=(), origin="analyst") -> dict:
    return {"id": None, "kind": kind, "text": text, "fact_ids": list(fact_ids), "calc_ids": list(calc_ids),
            "risk_ids": list(risk_ids), "origin": origin, "review": {"status": "pending"}}


# ------------------------------------------------------------------ claim validation
_NUM_IN_TEXT = re.compile(r"(?<![\w.])(?:US\$|C\$|A\$|\$)?(\d[\d,]*(?:\.\d+)?)\s*(million|billion|thousand|Mt|koz|Moz|%|"
                          r"g/t|m\b|oz\b|/oz)?", re.I)


def _numbers(text: str) -> list[tuple[Decimal, str]]:
    out = []
    t = re.sub(r"\[[^\]]*\]", " ", text)                       # bracketed source labels are not claims
    t = re.sub(r"\b100\s*%\s*(?:project\s+)?basis", " ", t, flags=re.I)   # basis label, checked separately
    t = re.sub(r"\bv\d+\b", " ", t)                              # formula versions
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", t)                 # dates handled separately
    t = re.sub(r"\b(?:hole|HP)-?\s*[\w-]*\d[\w-]*", " ", t, flags=re.I)
    t = re.sub(r"\b(?:Q[1-4]|H[12])\s+\d{4}\b", " ", t)
    t = re.sub(r"\b(19|20)\d{2}\b", " ", t)
    for m in _NUM_IN_TEXT.finditer(t):
        try:
            v = Decimal(m.group(1).replace(",", ""))
        except Exception:
            continue
        out.append((v, (m.group(2) or "").lower()))
    return out


def _supports_number(v: Decimal, unit: str, refs: list[dict]) -> bool:
    mult = {"million": Decimal(10) ** 6, "billion": Decimal(10) ** 9, "thousand": Decimal(10) ** 3,
            "mt": Decimal(10) ** 6, "koz": Decimal(10) ** 3, "moz": Decimal(10) ** 6}.get(unit, Decimal(1))
    target = v * mult
    for r in refs:
        cands = r.get("values", [])
        for c in cands:
            if c is None:
                continue
            c = Decimal(c)
            if c == 0 and target == 0:
                return True
            if c == 0:
                continue
            # the claim may round what the record holds: accept within half a unit of the printed precision
            dec = len(str(v).split(".")[1]) if "." in str(v) else 0
            half = Decimal(5) * Decimal(10) ** (-(dec + 1)) * mult
            if abs(c - target) <= half:
                return True
            if r.get("divisors"):
                for dv in r["divisors"]:
                    if abs(c / Decimal(dv) - v) <= Decimal(5) * Decimal(10) ** (-(dec + 1)):
                        return True
    return False


def _ref_records(store, actor, claim) -> tuple[list[dict], list[str]]:
    refs, problems = [], []
    for fid in claim.get("fact_ids", []):
        try:
            f = store.get(actor, "facts", fid)
        except NotFound:
            problems.append(f"cited fact {fid} does not exist in this workspace")
            continue
        if f["workflow_state"] != "reviewer_approved":
            problems.append(f"cited fact {fid} is not reviewer-approved (state: {f['workflow_state']})")
        d = D.metric(f["metric_id"])
        vals = [f["normalized_value"]] if f["value_kind"] == "decimal" else []
        if f.get("discount_rate"):
            vals.append(f["discount_rate"])
        # numbers that the record itself carries in its qualifiers (exercise price, the issuer's
        # true-width estimate, composite counts) are established by the same source
        for qv in (f["qualifiers"] or {}).values():
            if isinstance(qv, str):
                vals.extend(m.replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", qv))
        pub = None
        if f.get("version_id"):
            pub = store.get(actor, "document_versions", f["version_id"])["publication_date"]
        refs.append({"kind": "fact", "rec": f, "values": vals, "divisors": [d.display_divisor, "1000", "1000000"],
                     "dates": [x for x in (f["as_of_date"], f["effective_date"], f["period_end"], f["period_start"],
                                           f["qualifiers"].get("expiry"), pub) if x]})
    for cid in claim.get("calc_ids", []):
        try:
            c = store.get(actor, "calculations", cid)
        except NotFound:
            problems.append(f"cited calculation {cid} does not exist in this workspace")
            continue
        if c["status"] != "computed":
            problems.append(f"cited calculation {cid} was withheld: {'; '.join(c['missing'])}")
        if c["stale"]:
            problems.append(f"cited calculation {cid} is stale: {c['stale_reason']}")
        vals = [c["output_value"]] + [i["value"] for i in c["inputs"]]
        dates = [i.get("date") for i in c["inputs"] if i.get("date")] + \
                [v for k, v in (c["parameters"] or {}).items() if isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2}$", v)]
        refs.append({"kind": "calc", "rec": c, "values": vals, "divisors": ["1000000", "1000", "1"], "dates": dates})
    for rid in claim.get("risk_ids", []):
        try:
            r = store.get(actor, "risk_findings", rid)
            refs.append({"kind": "risk", "rec": r, "values": [], "dates": []})
        except NotFound:
            problems.append(f"cited risk {rid} does not exist in this workspace")
    return refs, problems


def validate_claim(store: Store, actor: Actor, claim: dict) -> dict:
    reasons = []
    text = claim["text"]
    refs, problems = _ref_records(store, actor, claim)
    reasons.extend(problems)
    kind = claim["kind"]
    if kind == "comparison":
        sid = (claim.get("origin") or "").split("snapshot:", 1)[-1]
        try:
            s = store.get(actor, "comparison_snapshots", sid)
        except NotFound:
            return {"status": "unsupported", "reasons": ["the comparison snapshot it came from does not exist"]}
        if s["stale"]:
            return {"status": "unsupported", "reasons": [f"comparison snapshot is stale: {s['stale_reason']}"]}
        rv = claim.get("review", {}).get("status")
        return {"status": "supported" if rv == "approved" else "needs_reviewer",
                "reasons": [] if rv == "approved" else ["comparison awaiting reviewer approval"]}
    if kind == "risk":
        ok = bool(claim.get("risk_ids")) and not problems
        return {"status": "supported" if ok else "unsupported",
                "reasons": reasons or ([] if ok else ["no risk record referenced"])}
    if kind == "factual" and not refs:
        return {"status": "unsupported", "reasons": ["no evidence reference: a factual claim must cite facts or "
                                                     "calculations"]}
    # every number must be established by the cited records
    for v, unit in _numbers(text):
        if not _supports_number(v, unit, refs):
            reasons.append(f"the number '{v}{(' ' + unit) if unit else ''}' is not established by the cited records")
    # every date must be a date of the cited records (bracketed source labels excluded)
    ref_dates = {d for r in refs for d in r["dates"]}
    for d in all_dates(re.sub(r"\[[^\]]*\]", " ", text)):
        if d not in ref_dates:
            reasons.append(f"the date {d} is not a date of the cited records (cited: {', '.join(sorted(ref_dates)) or 'none'})")
    low = text.lower()
    facts_ = [r["rec"] for r in refs if r["kind"] == "fact"]
    calcs_ = [r["rec"] for r in refs if r["kind"] == "calc"]
    # category: resources are not reserves; inferred is not M&I
    if re.search(r"\breserves?\b", low) and facts_ and not any(f["metric_id"] in D.RESERVE_METRICS for f in facts_) \
            and not re.search(r"not (?:mineral )?reserves|are not reserves|no reserves", low):
        reasons.append("the claim refers to reserves; the cited records are not reserve estimates")
    for f in facts_:
        cat = f.get("resource_category")
        if cat == "inferred" and re.search(r"measured|indicated|m&i", low) and "inferred" not in low:
            reasons.append("the claim describes Measured/Indicated ounces; the cited record is Inferred")
        if cat in ("measured_indicated", "indicated", "measured") and "inferred" in low and \
                not re.search(r"(?:excludes?|excluding|not including)\s+inferred", low):
            reasons.append("the claim refers to Inferred; the cited record is Measured/Indicated")
        if f["metric_id"] == "permit_status":
            st = f["normalized_value"]
            if st != "issued" and re.search(r"\b(issued|granted|received|approved|permitted|fully permitted|in hand)\b", low) \
                    and not re.search(r"not (?:yet )?(?:been )?(?:issued|granted|received|approved)", low):
                reasons.append(f"the claim states the authorization was issued/approved; the cited status is "
                               f"'{D.PERMIT_STATUSES[st]}'")
        if f["metric_id"] == "drill_intercept_length" and "true width" in low and \
                not re.search(r"true width[^.]{0,40}(not known|unknown|not established|estimate)", low):
            reasons.append("the claim calls a down-hole intercept a true width")
        if f["attribution"] in ("issuer_management", "qualified_person") and f["evidence_type"] in ("reported", "forecast") \
                and not ATTRIBUTION_WORDS.search(text):
            reasons.append("an issuer statement is presented as established fact; attribute it (e.g. 'the company reports')")
        if f["evidence_type"] == "forecast" and not FORECAST_WORDS.search(text):
            reasons.append("the cited value is a forecast/estimate; the claim must say so")
        if f["metric_id"] == "npv":
            if f["tax_basis"] and not re.search(f["tax_basis"].replace("_", "[- ]"), low):
                reasons.append(f"the claim omits the NPV tax basis ({f['tax_basis'].replace('_', '-')})")
            if f["discount_rate"] and not re.search(re.escape(f["discount_rate"]) + r"\s*%", text):
                reasons.append(f"the claim omits the NPV discount rate ({f['discount_rate']}%)")
            if re.search(r"equity value|company is worth|worth\b|market value of the company", low):
                reasons.append("project NPV is not company equity value")
    for c in calcs_:
        if c["formula_id"] == "market_cap" and re.search(r"enterprise value|\bev\b", low):
            reasons.append("the cited calculation is market capitalisation, not enterprise value")
        if c["formula_id"] == "attributable_npv" and re.search(r"equity value|worth", low) and \
                not re.search(r"not (?:company )?equity value", low):
            reasons.append("an attributable NPV is not company equity value")
        if c["formula_id"] == "runway" and re.search(r"\b(today|currently|current cash|now has)\b", low):
            reasons.append("runway is measured from the dated cash balance, not from today")
    if re.search(r"\b(will|certainly|guaranteed|definitely)\b", low) and kind == "factual":
        reasons.append("certainty language is not supported by evidence; restate as an attributed expectation")
    if kind == "interpretive":
        if reasons:
            return {"status": "unsupported", "reasons": reasons}
        rv = claim.get("review", {}).get("status")
        return {"status": "supported" if rv == "approved" else "needs_reviewer",
                "reasons": [] if rv == "approved" else ["interpretive claim awaiting reviewer approval"]}
    return {"status": "unsupported" if reasons else "supported", "reasons": reasons}


# ------------------------------------------------------------------ memo lifecycle
def create_memo(store: Store, actor: Actor, company_id: str, title: str, thesis_id: str | None = None,
                peer_set_id: str | None = None) -> dict:
    store.get(actor, "companies", company_id)
    now = config.iso_now()
    with store.db.tx():
        m = store.insert(actor, "memos", {"company_id": company_id, "title": title, "thesis_id": thesis_id,
                                          "peer_set_id": peer_set_id, "created_by": actor.user_id, "created_at": now})
        body = draft_body(store, actor, company_id, thesis_id, peer_set_id)
        v = store.insert(actor, "memo_versions", {"memo_id": m["id"], "version_no": 1, "status": "draft",
                                                  "body": body, "author": actor.user_id, "created_at": now})
        _link_version(store, actor, v["id"], body)
        store.audit(actor, "memo_created", m["id"])
    return {"memo": m, "version": store.get(actor, "memo_versions", v["id"])}


KEY_FACT_METRICS = ["cash_unrestricted", "total_debt", "shares_outstanding_basic", "warrants_outstanding",
                    "options_outstanding", "resource_contained_metal", "reserve_contained_metal", "npv", "irr",
                    "initial_capex", "commodity_price_assumption", "met_test_recovery",
                    "plant_recovery_assumption", "permit_status", "ownership_interest", "disclosure_signal",
                    "drill_intercept_length"]


def draft_body(store, actor, company_id, thesis_id, peer_set_id) -> dict:
    from . import diligence as DG, risks as R
    sections = {k: [] for k, _ in SECTIONS}
    if thesis_id:
        tv = store.find(actor, "thesis_versions", thesis_id=thesis_id, order="version_no")[-1]
        sections["thesis"].append(_claim("interpretive", tv["thesis_text"], origin="thesis"))
        sections["counter_thesis"].append(_claim("interpretive", tv["counter_thesis_text"], origin="thesis"))
    for mid in KEY_FACT_METRICS:
        rows = F.current(store, actor, company_id, mid, approved_only=True)
        rows = [f for f in rows if not f["qualifiers"].get("zone")]
        if mid in ("resource_contained_metal", "reserve_contained_metal"):
            latest = max((f["effective_date"] or "" for f in rows), default="")
            rows = [f for f in rows if f["effective_date"] == latest]
        for f in sorted(rows, key=lambda f: (f["as_of_date"] or f["effective_date"] or "", f["id"])):
            sections["material_facts"].append(_claim("factual", fact_claim_text(store, actor, f), fact_ids=[f["id"]],
                                                     origin="template"))
    for c in calc.run_standard(store, actor, company_id):
        if c["status"] == "computed":
            sections["valuation"].append(_claim("factual", f"{c['label']}: {c['display_value']} "
                                                f"(calculation {c['formula_id']} v{c['formula_version']}).",
                                                calc_ids=[c["id"]], origin="template"))
        else:
            sections["valuation"].append(_claim("withheld_calculation",
                                                f"{c['label']}: withheld — {'; '.join(c['missing'])}",
                                                calc_ids=[c["id"]], origin="template"))
    for r in R.register(store, actor, company_id):
        if r["status"] in ("dismissed",):
            continue
        sections["risks"].append(_claim("risk", r["title"], risk_ids=[r["id"]], origin="register"))
    if peer_set_id:
        snaps = store.find(actor, "comparison_snapshots", peer_set_id=peer_set_id, order="created_at")
        if snaps:
            s = snaps[-1]
            for obs in s["body"]["observations"]:
                sections["alternatives"].append(_claim("comparison", obs, origin=f"snapshot:{s['id']}"))
    for q in store.find(actor, "diligence_questions", company_id=company_id, status="open"):
        sections["diligence"].append(_claim("open_question", q["question"], origin=f"question:{q['id']}"))
    n = 0
    for k in sections:
        for c in sections[k]:
            n += 1
            c["id"] = f"c{n}"
    return {"sections": sections, "thesis_id": thesis_id, "peer_set_id": peer_set_id,
            "snapshot_id": (store.find(actor, "comparison_snapshots", peer_set_id=peer_set_id, order="created_at")[-1]["id"]
                            if peer_set_id and store.find(actor, "comparison_snapshots", peer_set_id=peer_set_id) else None)}


def _link_version(store, actor, version_id, body) -> None:
    for sec in body["sections"].values():
        for c in sec:
            for f in c.get("fact_ids", []):
                lineage.link(store, actor, "fact", f, "memo_version", version_id)
            for k in c.get("calc_ids", []):
                lineage.link(store, actor, "calculation", k, "memo_version", version_id)
    if body.get("snapshot_id"):
        lineage.link(store, actor, "snapshot", body["snapshot_id"], "memo_version", version_id)


def _editable(store, actor, version_id) -> dict:
    v = store.get(actor, "memo_versions", version_id)
    if v["status"] != "draft":
        raise Invalid(f"version is '{v['status']}'; only drafts can be edited — create a new version")
    store.require(actor, "write")
    return v


def add_claim(store: Store, actor: Actor, version_id: str, section: str, kind: str, text: str,
              fact_ids=(), calc_ids=(), risk_ids=(), origin: str = "analyst") -> dict:
    if section not in dict(SECTIONS):
        raise Invalid("unknown section")
    if kind not in ("factual", "interpretive"):
        raise Invalid("analyst claims are factual or interpretive")
    if origin not in ("analyst", "claude"):
        raise Invalid("origin must be analyst or claude")
    v = _editable(store, actor, version_id)
    body = v["body"]
    n = 1 + max((int(c["id"][1:]) for s in body["sections"].values() for c in s), default=0)
    c = _claim(kind, text, fact_ids, calc_ids, risk_ids, origin=origin)
    c["id"] = f"c{n}"
    body["sections"][section].append(c)
    with store.db.tx():
        store.update(actor, "memo_versions", version_id, {"body": body})
        _link_version(store, actor, version_id, {"sections": {section: [c]}})
    c["validation"] = validate_claim(store, actor, c)
    return c


def remove_claim(store: Store, actor: Actor, version_id: str, claim_id: str, reason: str) -> None:
    v = _editable(store, actor, version_id)
    body = v["body"]
    for sec, claims in body["sections"].items():
        for c in claims:
            if c["id"] == claim_id:
                if c["kind"] == "risk":
                    raise Invalid("risk items cannot be removed from a memo; dismiss the risk in the register "
                                  "with a reason instead")
                claims.remove(c)
                body.setdefault("removed", []).append({"claim": c, "reason": reason, "by": actor.user_id,
                                                       "at": config.iso_now()})
                store.update(actor, "memo_versions", version_id, {"body": body})
                return
    raise NotFound(claim_id)


def review_claim(store: Store, actor: Actor, version_id: str, claim_id: str, decision: str, reason: str = "") -> None:
    if not actor.can("review"):
        raise AccessDenied("claims are approved by a reviewer")
    v = store.get(actor, "memo_versions", version_id)
    if v["status"] not in ("draft", "in_review"):
        raise Invalid("this version is not open for review")
    if v["author"] == actor.user_id:
        raise AccessDenied("the memo author cannot approve its claims")
    if decision not in ("approved", "rejected"):
        raise Invalid("decision must be approved or rejected")
    body = v["body"]
    for claims in body["sections"].values():
        for c in claims:
            if c["id"] == claim_id:
                if decision == "approved":
                    pre = validate_claim(store, actor, {**c, "review": {"status": "approved"}})
                    if pre["status"] != "supported":
                        raise Invalid("this claim cannot be approved: " + "; ".join(pre["reasons"]))
                c["review"] = {"status": decision, "by": actor.user_id, "at": config.iso_now(), "reason": reason}
                store.update(actor, "memo_versions", version_id, {"body": body})
                store.audit(actor, f"claim_{decision}", f"{version_id}:{claim_id}")
                return
    raise NotFound(claim_id)


def review_supported_claims(store: Store, actor: Actor, version_id: str, reason: str) -> dict:
    """Reviewer action: approve each claim that passes validation, one decision
    per claim (recorded individually). Unsupported claims are left unapproved
    and reported back."""
    if not reason.strip():
        raise Invalid("a review reason is required")
    v = store.get(actor, "memo_versions", version_id)
    done, skipped = [], []
    for claims in v["body"]["sections"].values():
        for c in claims:
            if c["kind"] not in ("factual", "interpretive", "comparison") or c["review"].get("status") == "approved":
                continue
            try:
                review_claim(store, actor, version_id, c["id"], "approved", reason)
                done.append(c["id"])
            except Invalid as exc:
                skipped.append({"id": c["id"], "reason": str(exc)})
    return {"approved": done, "not_approved": skipped}


def submit(store: Store, actor: Actor, version_id: str) -> None:
    v = _editable(store, actor, version_id)
    store.update(actor, "memo_versions", version_id, {"status": "in_review", "submitted_at": config.iso_now()})
    store.audit(actor, "memo_submitted", version_id)


def approval_blockers(store: Store, actor: Actor, version_id: str) -> list[str]:
    from . import risks as R
    v = store.get(actor, "memo_versions", version_id)
    memo = store.get(actor, "memos", v["memo_id"])
    blockers = []
    body = v["body"]
    for sec, claims in body["sections"].items():
        for c in claims:
            if c["kind"] in ("factual", "interpretive", "comparison"):
                res = validate_claim(store, actor, c)
                if res["status"] == "unsupported":
                    blockers.append(f"{c['id']} ({sec}): " + "; ".join(res["reasons"]))
                elif c["review"].get("status") != "approved":
                    blockers.append(f"{c['id']} ({sec}): awaiting reviewer approval")
    included = {r for claims in body["sections"].values() for c in claims for r in c.get("risk_ids", [])}
    for r in R.register(store, actor, memo["company_id"]):
        if r["status"] in ("dismissed", "resolved"):
            continue
        if r["id"] not in included:
            blockers.append(f"risk '{r['title']}' is in the register but not in the memo")
    if not body["sections"].get("counter_thesis"):
        blockers.append("the memo has no counter-thesis")
    if v["stale"]:
        blockers.append(f"the version is stale: {v['stale_reason']}")
    for sec, claims in body["sections"].items():
        for c in claims:
            for cid in c.get("calc_ids", []):
                cc = store.get(actor, "calculations", cid)
                if cc["stale"]:
                    blockers.append(f"{c['id']}: calculation {cid} is stale ({cc['stale_reason']})")
    if v["author"] == actor.user_id:
        blockers.append("the approver must not be the author")
    if not actor.can("review"):
        blockers.append("approval requires the reviewer role")
    if v["status"] != "in_review":
        blockers.append(f"version status is '{v['status']}', not 'in_review'")
    return blockers


def approve(store: Store, actor: Actor, version_id: str, rationale: str) -> dict:
    if not actor.can("review"):
        raise AccessDenied("approval requires the reviewer role")
    blockers = approval_blockers(store, actor, version_id)
    if blockers:
        raise Invalid("cannot approve: " + " | ".join(blockers))
    v = store.get(actor, "memo_versions", version_id)
    r = render(store, actor, version_id)
    digest = hashlib.sha256(dumps({"body": v["body"], "rendered": r["sections"]}).encode()).hexdigest()
    with store.db.tx():
        for old in store.find(actor, "memo_versions", memo_id=v["memo_id"], status="approved"):
            store.update(actor, "memo_versions", old["id"], {"status": "superseded"})
        store.update(actor, "memo_versions", version_id, {
            "status": "approved", "approved_by": actor.user_id, "approved_at": config.iso_now(),
            "content_sha256": digest, "evidence_cutoff": r["evidence_cutoff"]})
        store.insert(actor, "review_decisions", {"target_kind": "memo_version", "target_id": version_id,
                                                 "decision": "approve", "from_state": "in_review",
                                                 "to_state": "approved", "reason": rationale,
                                                 "actor": actor.user_id, "at": config.iso_now()})
        store.audit(actor, "memo_approved", version_id, {"sha256": digest})
    return store.get(actor, "memo_versions", version_id)


def new_version(store: Store, actor: Actor, memo_id: str, refresh: bool = False) -> dict:
    """A new draft. With refresh=True the body is regenerated from current
    approved records (analyst claims are carried over and re-validated)."""
    store.require(actor, "write")
    memo = store.get(actor, "memos", memo_id)
    prev = store.find(actor, "memo_versions", memo_id=memo_id, order="version_no")[-1]
    body = prev["body"]
    if refresh:
        fresh = draft_body(store, actor, memo["company_id"], memo["thesis_id"], memo["peer_set_id"])
        for sec, claims in body["sections"].items():
            for c in claims:
                if c.get("origin") in ("analyst", "claude"):
                    fresh["sections"][sec].append(c)
        n = 0
        for claims in fresh["sections"].values():
            for c in claims:
                n += 1
                c["id"] = f"c{n}"
        body = fresh
    for claims in body["sections"].values():
        for c in claims:
            c["review"] = {"status": "pending"}
    with store.db.tx():
        v = store.insert(actor, "memo_versions", {"memo_id": memo_id, "version_no": prev["version_no"] + 1,
                                                  "status": "draft", "body": body, "author": actor.user_id,
                                                  "created_at": config.iso_now()})
        _link_version(store, actor, v["id"], body)
    return store.get(actor, "memo_versions", v["id"])


# ------------------------------------------------------------------ rendering
def render(store: Store, actor: Actor, version_id: str) -> dict:
    from . import risks as R
    v = store.get(actor, "memo_versions", version_id)
    memo = store.get(actor, "memos", v["memo_id"])
    company = store.get(actor, "companies", memo["company_id"])
    cov = ingest.coverage(store, actor, memo["company_id"])
    risk_by_id = {r["id"]: r for r in R.register(store, actor, memo["company_id"])}
    sections, withheld, unresolved, refs_out, pub_dates = [], [], [], {}, []
    # An approved (or superseded-approved) version is a historical record: it renders exactly as
    # approved. Later changes to its evidence are reported alongside it, never by rewriting it.
    immutable = v["status"] in ("approved", "superseded")
    for key, title in SECTIONS:
        out = []
        for c in v["body"]["sections"].get(key, []):
            item = {"id": c["id"], "kind": c["kind"], "text": c["text"], "review": c["review"], "evidence": []}
            if c["kind"] in ("factual", "interpretive", "comparison"):
                res = validate_claim(store, actor, c)
                item["validation"] = res
                if res["status"] == "unsupported" and immutable:
                    item["changed_since_approval"] = res["reasons"]
                    unresolved.append(f"Since approval, claim {c['id']}: " + "; ".join(res["reasons"]))
                elif res["status"] == "unsupported":
                    withheld.append({"id": c["id"], "section": title, "text": c["text"], "reasons": res["reasons"]})
                    unresolved.append(f"Withheld claim {c['id']}: " + "; ".join(res["reasons"]))
                    continue
                elif res["status"] == "needs_reviewer" or c["review"].get("status") != "approved":
                    unresolved.append(f"Claim {c['id']} awaiting reviewer approval")
            if c["kind"] == "withheld_calculation":
                unresolved.append(c["text"])
            if c["kind"] == "open_question":
                unresolved.append("Open diligence question: " + c["text"])
            for fid in c.get("fact_ids", []):
                try:
                    f = store.get(actor, "facts", fid)
                except NotFound:
                    continue
                loc = store.get(actor, "source_locations", f["location_id"]) if f["location_id"] else None
                ver = store.get(actor, "document_versions", f["version_id"]) if f["version_id"] else None
                doc = store.get(actor, "documents", ver["document_id"]) if ver else None
                if ver and ver["publication_date"]:
                    pub_dates.append(ver["publication_date"])
                ref = {"fact_id": fid, "metric": D.metric(f["metric_id"]).label, "state": f["workflow_state"],
                       "evidence_type": f["evidence_type"], "document": doc["title"] if doc else None,
                       "version_id": f["version_id"], "sha256": ver["sha256"] if ver else None,
                       "page": loc["page_no"] if loc else None, "cell": loc["cell_ref"] if loc else None,
                       "quote": loc["quote"] if loc else None, "published": ver["publication_date"] if ver else None,
                       "definition_version": f["definition_version"]}
                item["evidence"].append(ref)
                refs_out[fid] = ref
            for cid in c.get("calc_ids", []):
                cc = store.get(actor, "calculations", cid)
                item["evidence"].append({"calc_id": cid, "formula": f"{cc['formula_id']} v{cc['formula_version']}",
                                         "status": cc["status"], "stale": bool(cc["stale"]), "inputs": cc["inputs"],
                                         "warnings": cc["warnings"], "caveats": cc["caveats"]})
            if c["kind"] == "risk":
                for rid in c["risk_ids"]:
                    r = risk_by_id.get(rid)
                    if not r:
                        continue
                    item["risk"] = {"category": D.RISK_CATEGORIES[r["category"]],
                                    "status": D.RISK_STATUSES[r["status"]],
                                    "attention": (f"Marked for attention: {r['attention_reason']}" if r["attention"] else ""),
                                    "consequence": r["consequence"], "mitigants": r["mitigants"],
                                    "unresolved_questions": r["unresolved_questions"],
                                    "monitoring_trigger": r["monitoring_trigger"],
                                    "supporting": [_ev(store, actor, e) for e in r["evidence"] if e["stance"] == "supporting"],
                                    "contrary": [_ev(store, actor, e) for e in r["evidence"] if e["stance"] == "contrary"]}
                    if not item["risk"]["contrary"]:
                        item["risk"]["contrary_note"] = "No contrary evidence recorded."
            out.append(item)
        sections.append({"key": key, "title": title, "items": out})
    status_label = {"draft": "DRAFT — not approved", "in_review": "IN REVIEW — not approved",
                    "approved": f"APPROVED by {v['approved_by']} on {(v['approved_at'] or '')[:10]}",
                    "superseded": "SUPERSEDED by a later approved version"}[v["status"]]
    if v["stale"]:
        status_label += f" — STALE: {v['stale_reason']}"
    for x in cov["ingestion_failed"]:
        unresolved.append(f"Ingestion failed: {x['title']}")
    for x in cov["unreadable_pages"]:
        unresolved.append(f"Unreadable pages not reviewed: {x['title']} p.{', '.join(map(str, x['pages']))}")
    return {"memo_id": memo["id"], "version_id": v["id"], "version_no": v["version_no"], "title": memo["title"],
            "company": company["name"], "status": v["status"], "status_label": status_label,
            "analysis_time": config.iso_now(), "evidence_cutoff": max(pub_dates) if pub_dates else cov["evidence_cutoff"],
            "coverage": {"documents_reviewed": len(cov["documents_reviewed"]),
                         "documents": [f"{d['title']} ({d['publication_date']})" for d in cov["documents_reviewed"]],
                         "complete": cov["complete"]},
            "sections": sections, "withheld_claims": withheld, "unresolved": unresolved,
            "content_sha256": v["content_sha256"], "approved_by": v["approved_by"], "approved_at": v["approved_at"],
            "synthetic": bool(company.get("synthetic")),
            "notice": ("Evidence-linked research record. Not a recommendation, rating or price target. "
                       "Reviewer approval confirms that claims match their cited sources; it does not "
                       "independently verify geological, legal or commercial facts.")}


def _ev(store, actor, e) -> dict:
    out = {"date": e["evidence_date"], "note": e["note"]}
    if e.get("location_id"):
        loc = store.get(actor, "source_locations", e["location_id"])
        ver = store.get(actor, "document_versions", loc["version_id"])
        doc = store.get(actor, "documents", ver["document_id"])
        out.update({"document": doc["title"], "page": loc["page_no"], "quote": loc["quote"][:300],
                    "location_id": loc["id"]})
    if e.get("fact_id"):
        out["fact_id"] = e["fact_id"]
    return out
