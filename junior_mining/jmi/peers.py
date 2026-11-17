"""Peer generation, analyst approval and comparison snapshots (brief §10).

Candidates are generated from commodity, stage, jurisdiction, deposit and
process characteristics, ownership and investability, and every inclusion is
explained. The analyst approves, excludes or overrides each one with a
recorded rationale. If strict peers are unavailable, broader comparators are
labelled as such with their limitations.

A snapshot shares one market-data date and keeps the differences between
that date and each company's financial-report dates. Incompatible metrics are
withheld with a reason. Outputs describe differences on specified measures
("under these inputs, B has a lower EV per M&I ounce; these differences
remain unresolved") — they never name an overall winner, and the default
ordering is alphabetical, not by any metric.
"""

from __future__ import annotations

from decimal import Decimal

from . import calc, config, entities, facts as F, lineage
from . import definitions as D
from .auth import Actor
from .store import Invalid, Store


def _words(s: str | None) -> set:
    import re
    return {w for w in re.findall(r"[a-z]+", (s or "").lower()) if len(w) > 2}


def _investability(store, actor, company_id) -> tuple[list, list]:
    reasons, diffs = [], []
    listings = store.find(actor, "listings", company_id=company_id)
    if listings:
        l = listings[0]
        reasons.append(f"listed ({l['exchange']}:{l['ticker']})")
    else:
        diffs.append("no listing recorded")
    adv = F.latest(store, actor, company_id, "average_daily_volume", approved_only=False)
    if adv:
        reasons.append(f"average daily volume {int(Decimal(adv['normalized_value'])):,} shares "
                       f"({adv['qualifiers'].get('window')}, {adv['as_of_date']}; {adv['workflow_state']})")
    else:
        diffs.append("no trading-volume data uploaded")
    return reasons, diffs


def generate_candidates(store: Store, actor: Actor, subject_company_id: str,
                        subject_project_id: str) -> list[dict]:
    subj = store.get(actor, "projects", subject_project_id)
    out = []
    for c in store.find(actor, "companies"):
        if c["id"] == subject_company_id:
            continue
        for p in entities.projects_of(store, actor, c["id"]):
            reasons, diffs = [], []
            if p["commodity"] and p["commodity"] == subj["commodity"]:
                reasons.append(f"same primary commodity ({p['commodity']})")
            else:
                diffs.append(f"different commodity ({p['commodity'] or 'not recorded'} vs {subj['commodity']})")
            same_group = D.STAGE_GROUP.get(p["stage"] or "") == D.STAGE_GROUP.get(subj["stage"] or "")
            if p["stage"] == subj["stage"]:
                reasons.append(f"same stage ({D.STAGE_LABELS.get(p['stage'], p['stage'])})")
            elif same_group:
                reasons.append(f"same stage group ({D.STAGE_GROUP[p['stage']]})")
                diffs.append(f"stage differs: {D.STAGE_LABELS.get(p['stage'])} vs "
                             f"{D.STAGE_LABELS.get(subj['stage'])} — study maturity is not like-for-like")
            else:
                diffs.append(f"stage differs: {D.STAGE_LABELS.get(p['stage'] or '', 'not recorded')} vs "
                             f"{D.STAGE_LABELS.get(subj['stage'] or '', 'not recorded')}")
            if p["jurisdiction"] and p["jurisdiction"] == subj["jurisdiction"]:
                reasons.append(f"same jurisdiction ({p['jurisdiction']})")
            elif p["country"] and p["country"] == subj["country"]:
                reasons.append(f"same country ({p['country']})")
                diffs.append(f"different jurisdiction ({p['jurisdiction']})")
            else:
                diffs.append(f"different jurisdiction ({p['jurisdiction'] or 'not recorded'})")
            shared = _words(p["deposit_type"]) & _words(subj["deposit_type"])
            if shared:
                reasons.append(f"deposit characteristics in common: {', '.join(sorted(shared))}")
            else:
                diffs.append(f"deposit type differs ({p['deposit_type'] or 'not recorded'})")
            if p["process_route"] and p["process_route"] == subj["process_route"]:
                reasons.append(f"same process route ({p['process_route']})")
            else:
                diffs.append(f"process route differs ({p['process_route'] or 'not recorded'} vs "
                             f"{subj['process_route'] or 'not recorded'})")
            oi = p["interest"]
            if oi["interest_pct"] is None:
                diffs.append("ownership interest not established")
            elif Decimal(oi["interest_pct"]) < 100:
                diffs.append(f"{oi['interest_pct']}% {oi['interest_kind'].replace('_', ' ')} interest — "
                             "attributable basis needed for company-level comparison")
            ir, idf = _investability(store, actor, c["id"])
            reasons += ir
            diffs += idf
            strict = (p["commodity"] == subj["commodity"]) and same_group
            out.append({"company_id": c["id"], "company": c["name"], "project_id": p["id"], "project": p["name"],
                        "classification": "strict_peer" if strict else "broader_comparator",
                        "inclusion_reasons": reasons, "differences": diffs})
    return sorted(out, key=lambda r: (r["company"], r["project"]))


def create_peer_set(store: Store, actor: Actor, subject_company_id: str, subject_project_id: str,
                    name: str) -> dict:
    with store.db.tx():
        ps = store.insert(actor, "peer_sets", {
            "subject_company_id": subject_company_id, "subject_project_id": subject_project_id, "name": name,
            "status": "draft", "created_by": actor.user_id, "created_at": config.iso_now()})
        for cand in generate_candidates(store, actor, subject_company_id, subject_project_id):
            store.insert(actor, "peer_members", {
                "peer_set_id": ps["id"], "company_id": cand["company_id"], "project_id": cand["project_id"],
                "classification": cand["classification"], "inclusion_reasons": cand["inclusion_reasons"],
                "differences": cand["differences"], "decision": "proposed"})
        store.audit(actor, "peer_set_created", ps["id"])
    return ps


def decide(store: Store, actor: Actor, member_id: str, decision: str, rationale: str,
           classification: str | None = None) -> None:
    if decision not in ("approved", "excluded"):
        raise Invalid("decision must be approved or excluded")
    if not rationale.strip():
        raise Invalid("every inclusion or exclusion needs a recorded rationale")
    m = store.get(actor, "peer_members", member_id)
    ps = store.get(actor, "peer_sets", m["peer_set_id"])
    if ps["status"] == "approved":
        raise Invalid("this peer set is approved; create a new set to change membership")
    patch = {"decision": decision, "decision_rationale": rationale, "decided_by": actor.user_id,
             "decided_at": config.iso_now()}
    if classification:
        if classification not in ("strict_peer", "broader_comparator"):
            raise Invalid("classification must be strict_peer or broader_comparator")
        patch["classification"] = classification
        patch["decision_rationale"] = f"{rationale} (classification overridden to {classification})"
    store.update(actor, "peer_members", member_id, patch)
    store.audit(actor, f"peer_{decision}", member_id, rationale[:200])


def approve_set(store: Store, actor: Actor, peer_set_id: str, rationale: str) -> None:
    members = store.find(actor, "peer_members", peer_set_id=peer_set_id)
    if any(m["decision"] == "proposed" for m in members):
        raise Invalid("every proposed member must be approved or excluded first")
    if not any(m["decision"] == "approved" for m in members):
        raise Invalid("an approved peer set needs at least one approved member")
    if not rationale.strip():
        raise Invalid("approval needs a rationale")
    store.update(actor, "peer_sets", peer_set_id, {"status": "approved", "approved_by": actor.user_id,
                                                   "approved_at": config.iso_now(),
                                                   "approval_rationale": rationale})
    store.audit(actor, "peer_set_approved", peer_set_id)


# ------------------------------------------------------------------ snapshot
def _reported(store, actor, company_id, project_id, metric, **match) -> dict:
    f = F.latest(store, actor, company_id, metric, project_id, approved_only=True, **match)
    if not f:
        pend = F.latest(store, actor, company_id, metric, project_id, approved_only=False, **match)
        return {"status": "withheld", "reason": ("extracted but not reviewer-approved" if pend
                                                 else "not established in documents reviewed")}
    d = D.metric(metric)
    from .quantities import fmt
    if f["value_kind"] == "enum":
        disp = D.PERMIT_STATUSES.get(f["normalized_value"], f["normalized_value"])
    else:
        disp = f"{f['currency'] or ''} {fmt(Decimal(f['normalized_value']), d.display_decimals, d.display_divisor)}" \
               f"{d.display_suffix}".strip()
    return {"status": "reported", "fact_id": f["id"], "display": disp, "value": f["normalized_value"],
            "unit": f["unit"], "currency": f["currency"], "study_type": f["study_type"],
            "effective_date": f["effective_date"], "as_of_date": f["as_of_date"], "tax_basis": f["tax_basis"],
            "discount_rate": f["discount_rate"], "evidence_type": f["evidence_type"],
            "price_case": f["qualifiers"].get("price_case"), "qualifiers": f["qualifiers"]}


def _calc_cell(store, actor, r: calc.CalcResult, company_id) -> dict:
    cid = calc.save(store, actor, r, company_id)
    if r.status != "computed":
        return {"status": "withheld", "reason": "; ".join(r.missing), "calc_id": cid}
    return {"status": "computed", "calc_id": cid, "display": r.display(), "value": str(r.value), "unit": r.unit,
            "warnings": r.warnings, "parameters": {k: v for k, v in r.parameters.items() if k != "table"}}


METRIC_ROWS = [
    ("market_cap", "Basic market capitalisation"),
    ("enterprise_value", "Enterprise value (explicit bridge)"),
    ("ev_per_mi_oz_100", "EV per Measured & Indicated oz (100% basis)"),
    ("ev_per_mi_oz_attr", "EV per attributable Measured & Indicated oz"),
    ("ev_per_pp_oz_100", "EV per Proven & Probable oz (100% basis)"),
    ("npv_after_tax", "Reported after-tax project NPV (100% basis)"),
    ("attributable_npv", "Attributable share of reported NPV (not equity value)"),
    ("irr_after_tax", "Reported after-tax IRR"),
    ("initial_capex", "Reported initial capital"),
    ("commodity_price", "Study gold-price assumption"),
    ("permit", "Latest permit status in documents reviewed"),
    ("adv", "Average daily volume"),
    ("cash_date_gap", "Days between balance-sheet date and market-data date"),
]


def build_snapshot(store: Store, actor: Actor, peer_set_id: str, market_data_date: str) -> dict:
    ps = store.get(actor, "peer_sets", peer_set_id)
    if ps["status"] != "approved":
        raise Invalid("comparisons are built only from an analyst-approved peer set")
    members = [m for m in store.find(actor, "peer_members", peer_set_id=peer_set_id) if m["decision"] == "approved"]
    entities_ = [{"company_id": ps["subject_company_id"], "project_id": ps["subject_project_id"], "role": "subject",
                  "classification": "subject", "reasons": [], "differences": []}] + \
                [{"company_id": m["company_id"], "project_id": m["project_id"], "role": "peer",
                  "classification": m["classification"], "reasons": m["inclusion_reasons"],
                  "differences": m["differences"], "rationale": m["decision_rationale"]} for m in members]
    excluded = [{"company": store.get(actor, "companies", m["company_id"])["name"],
                 "rationale": m["decision_rationale"]}
                for m in store.find(actor, "peer_members", peer_set_id=peer_set_id) if m["decision"] == "excluded"]
    rows = []
    used_calcs, used_facts = [], []
    for e in entities_:
        cid, pid = e["company_id"], e["project_id"]
        c = store.get(actor, "companies", cid)
        p = store.get(actor, "projects", pid)
        cells = {}
        price = F.latest(store, actor, cid, "share_price", approved_only=True, on_or_before=market_data_date)
        if not price or price["as_of_date"] != market_data_date:
            note = (f"no approved price on the market-data date {market_data_date}"
                    + (f" (latest approved: {price['as_of_date']})" if price else ""))
            for k in ("market_cap", "enterprise_value", "ev_per_mi_oz_100", "ev_per_mi_oz_attr", "ev_per_pp_oz_100"):
                cells[k] = {"status": "withheld", "reason": note}
        else:
            cells["market_cap"] = _calc_cell(store, actor, calc.market_cap(store, actor, cid, market_data_date), cid)
            cells["enterprise_value"] = _calc_cell(store, actor, calc.enterprise_value(store, actor, cid, market_data_date), cid)
            cells["ev_per_mi_oz_100"] = _calc_cell(store, actor, calc.ev_per_contained_oz(
                store, actor, cid, pid, "measured_indicated", "100%", market_data_date), cid)
            cells["ev_per_mi_oz_attr"] = _calc_cell(store, actor, calc.ev_per_contained_oz(
                store, actor, cid, pid, "measured_indicated", "attributable", market_data_date), cid)
            cells["ev_per_pp_oz_100"] = _calc_cell(store, actor, calc.ev_per_contained_oz(
                store, actor, cid, pid, "proven_probable", "100%", market_data_date), cid)
        cells["npv_after_tax"] = _reported(store, actor, cid, pid, "npv", tax_basis="after_tax")
        cells["attributable_npv"] = _calc_cell(store, actor, calc.attributable_npv(store, actor, cid, pid), cid)
        cells["irr_after_tax"] = _reported(store, actor, cid, pid, "irr", tax_basis="after_tax")
        cells["initial_capex"] = _reported(store, actor, cid, pid, "initial_capex")
        cells["commodity_price"] = _reported(store, actor, cid, pid, "commodity_price_assumption")
        cells["permit"] = _reported(store, actor, cid, pid, "permit_status")
        cells["adv"] = _reported(store, actor, cid, None, "average_daily_volume")
        cash = F.latest(store, actor, cid, "cash_unrestricted", approved_only=True)
        if cash and cash["as_of_date"]:
            from datetime import date
            gap = (date.fromisoformat(market_data_date) - date.fromisoformat(cash["as_of_date"])).days
            cells["cash_date_gap"] = {"status": "computed", "display": f"{gap} days (cash as at {cash['as_of_date']})",
                                      "value": str(gap), "fact_id": cash["id"]}
        else:
            cells["cash_date_gap"] = {"status": "withheld", "reason": "no approved balance-sheet date"}
        for v in cells.values():
            if v.get("calc_id"):
                used_calcs.append(v["calc_id"])
            if v.get("fact_id"):
                used_facts.append(v["fact_id"])
        rows.append({"company_id": cid, "company": c["name"], "project_id": pid, "project": p["name"],
                     "stage": D.STAGE_LABELS.get(p["stage"] or "", "not recorded"), "jurisdiction": p["jurisdiction"],
                     "role": e["role"], "classification": e["classification"], "reasons": e["reasons"],
                     "differences": e["differences"], "rationale": e.get("rationale", ""), "cells": cells})
    rows.sort(key=lambda r: (r["role"] != "subject", r["company"]))     # subject first, then alphabetical
    comparability = _comparability(rows)
    body = {"peer_set_id": peer_set_id, "peer_set_name": ps["name"], "market_data_date": market_data_date,
            "metric_rows": METRIC_ROWS, "rows": rows, "excluded": excluded, "comparability": comparability,
            "observations": _observations(rows), "explanations": _explanations(store, actor, rows),
            "method": {"formulas": {k: calc.FORMULAS[k].definition for k in
                                    ("market_cap", "enterprise_value", "ev_per_contained_oz", "attributable_npv")},
                       "ordering": "Subject first, then alphabetical. Sorting by a metric is a user action and "
                                   "does not establish an overall preference.",
                       "approval": {"approved_by": ps["approved_by"], "approved_at": ps["approved_at"],
                                    "rationale": ps["approval_rationale"]}},
            "analysis_time": config.iso_now()}
    with store.db.tx():
        snap = store.insert(actor, "comparison_snapshots", {"peer_set_id": peer_set_id,
                                                            "market_data_date": market_data_date, "body": body,
                                                            "created_by": actor.user_id,
                                                            "created_at": config.iso_now()})
        for cid in set(used_calcs):
            lineage.link(store, actor, "calculation", cid, "snapshot", snap["id"])
        for fid in set(used_facts):
            lineage.link(store, actor, "fact", fid, "snapshot", snap["id"])
        store.audit(actor, "snapshot_built", snap["id"], f"market_data_date={market_data_date}")
    return store.get(actor, "comparison_snapshots", snap["id"])


def _comparability(rows: list) -> dict:
    notes = {}

    def distinct(key, field):
        vals = {}
        for r in rows:
            c = r["cells"].get(key, {})
            if c.get("status") in ("reported", "computed"):
                v = c.get(field) if field in c else c.get("parameters", {}).get(field)
                vals.setdefault(str(v), []).append(r["company"])
        return vals

    for key in ("npv_after_tax", "irr_after_tax", "initial_capex"):
        st = distinct(key, "study_type")
        if len(st) > 1:
            notes.setdefault(key, []).append("Not like-for-like: study types differ — " + "; ".join(
                f"{(k or 'unstated').upper()}: {', '.join(v)}" for k, v in st.items()))
        ed = distinct(key, "effective_date")
        if len(ed) > 1:
            notes.setdefault(key, []).append("Study effective dates differ — " + "; ".join(
                f"{k}: {', '.join(v)}" for k, v in ed.items()))
    prices = {}
    for r in rows:
        c = r["cells"].get("commodity_price", {})
        if c.get("status") == "reported":
            prices.setdefault(c["display"], []).append(r["company"])
    if len(prices) > 1:
        notes.setdefault("npv_after_tax", []).append(
            "Gold-price assumptions differ — " + "; ".join(f"{k}: {', '.join(v)}" for k, v in prices.items())
            + ". Reported NPVs are shown as reported; they are not re-priced here.")
    for key in ("ev_per_mi_oz_100", "ev_per_mi_oz_attr"):
        rb = distinct(key, "reporting_basis")
        if len(rb) > 1:
            notes.setdefault(key, []).append("Resource reporting bases differ (inclusive vs exclusive of reserves) — "
                                             + "; ".join(f"{k}: {', '.join(v)}" for k, v in rb.items()))
        ed = distinct(key, "effective_date")
        if len(ed) > 1:
            notes.setdefault(key, []).append("Resource effective dates differ — " + "; ".join(
                f"{k}: {', '.join(v)}" for k, v in ed.items()))
    notes.setdefault("attributable_npv", []).append(
        "Attributable NPV is the ownership share of a reported project NPV. It is not company equity value.")
    notes.setdefault("ev_per_mi_oz_100", []).append(
        "Resource ounces are not reserves; Inferred ounces are excluded; categories are not combined.")
    return notes


def _observations(rows: list) -> list[str]:
    subj = next(r for r in rows if r["role"] == "subject")
    out = []
    for key, label in (("ev_per_mi_oz_100", "EV per M&I oz (100% basis)"),
                       ("ev_per_mi_oz_attr", "EV per attributable M&I oz"),
                       ("enterprise_value", "enterprise value")):
        sc = subj["cells"].get(key, {})
        for r in rows:
            if r is subj:
                continue
            pc = r["cells"].get(key, {})
            if sc.get("status") != "computed" or pc.get("status") != "computed":
                why = sc.get("reason") if sc.get("status") != "computed" else pc.get("reason")
                out.append(f"{label}: {subj['company']} vs {r['company']} — not compared ({why}).")
                continue
            if sc.get("unit") != pc.get("unit"):
                out.append(f"{label}: units differ ({sc.get('unit')} vs {pc.get('unit')}); not compared.")
                continue
            a, b = Decimal(sc["value"]), Decimal(pc["value"])
            rel = "lower" if b < a else "higher" if b > a else "the same"
            out.append(f"Under these inputs, {r['company']} has a {rel} {label} than {subj['company']} "
                       f"({pc['display']} vs {sc['display']}). Differences that remain unresolved: "
                       + ("; ".join(r["differences"]) or "none recorded") + ".")
    return out


def _explanations(store, actor, rows: list) -> dict:
    from . import risks as R
    subj = next(r for r in rows if r["role"] == "subject")
    sub_risks = [x for x in R.register(store, actor, subj["company_id"])
                 if x["status"] not in ("resolved", "dismissed")]
    disadvantages = [f"{subj['company']}: {x['title']} ({D.RISK_CATEGORIES[x['category']]}; "
                     f"{D.RISK_STATUSES[x['status']].split(' —')[0]})" for x in sub_risks]
    peer_adv = []
    for r in rows:
        if r is subj:
            continue
        pm = r["cells"].get("permit", {})
        if pm.get("status") == "reported":
            peer_adv.append(f"{r['company']}: permit status reported as '{pm['display']}'")
        npv = r["cells"].get("npv_after_tax", {})
        if npv.get("status") == "reported":
            peer_adv.append(f"{r['company']}: economics from a {(npv.get('study_type') or 'unstated').upper()} "
                            f"(effective {npv.get('effective_date')})")
        pp = r["cells"].get("ev_per_pp_oz_100", {})
        if pp.get("status") == "computed":
            peer_adv.append(f"{r['company']}: reports Proven & Probable reserves")
    reversals = []
    for r in rows:
        for k, c in r["cells"].items():
            if c.get("status") == "withheld":
                reversals.append(f"{r['company']} — {dict(METRIC_ROWS).get(k, k)}: {c['reason']}")
    open_q = [q["question"] for q in store.find(actor, "diligence_questions", company_id=subj["company_id"],
                                                 status="open")]
    return {"subject_disadvantages_that_could_explain_a_discount": disadvantages,
            "peer_characteristics_that_could_justify_a_premium": peer_adv,
            "missing_evidence_that_could_change_the_comparison": reversals + open_q[:10]}


def sort_rows(rows: list, metric_key: str, descending: bool = False) -> tuple[list, str]:
    """User-initiated sort by one objective metric. Withheld values sort last."""
    def k(r):
        c = r["cells"].get(metric_key, {})
        try:
            return (0, Decimal(c["value"]) * (-1 if descending else 1))
        except Exception:
            return (1, 0)
    return sorted(rows, key=k), (f"Sorted by {dict(METRIC_ROWS).get(metric_key, metric_key)} "
                                 f"({'descending' if descending else 'ascending'}). Sorting by one measure does not "
                                 "establish an overall preference.")
