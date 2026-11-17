"""Stage-aware diligence checklists, specialist questions and commitments.

Missing information creates a specific question and document request, not a
zero and not a guess. No checklist is ever labelled "complete diligence": the
strongest statement available is "every item reviewed by <reviewer> on
<date>", which describes what was done, not what is true.
"""

from __future__ import annotations

import re

from . import config, events
from .auth import Actor
from .definitions import STAGES
from .store import AccessDenied, Invalid, Store

# item_key: (title, specialist, required metrics, stages it applies to)
ITEMS = {
    "tenure": ("Land tenure and claim status from an official registry", "legal", [], STAGES),
    "ownership": ("Ownership interest, agreements and earn-in obligations", "legal",
                  ["ownership_interest"], STAGES),
    "capital_structure": ("Basic shares, warrants, options and convertibles", "financial",
                          ["shares_outstanding_basic"], STAGES),
    "cash_position": ("Unrestricted cash, restricted cash and debt with dates", "financial",
                      ["cash_unrestricted", "total_debt"], STAGES),
    "burn": ("Spending history and stated budget", "financial", ["period_cash_outflow"], STAGES),
    "royalties_streams": ("Royalties, streams and offtake encumbrances", "legal", [], STAGES),
    "drilling_qaqc": ("Drill data: QA/QC, true-width basis, assay certificates", "geology",
                      [], ("exploration", "resource", "pea", "pfs")),
    "resource_estimate": ("Current resource estimate: categories, cut-off, effective date, basis",
                          "geology", ["resource_contained_metal"], ("resource", "pea", "pfs", "fs", "construction")),
    "reserves": ("Reserve estimate (Proven/Probable) and conversion from resources", "geology",
                 ["reserve_contained_metal"], ("pfs", "fs", "construction", "operating")),
    "metallurgy": ("Metallurgical testwork coverage, variability and deleterious elements", "metallurgy",
                   ["met_test_recovery"], ("resource", "pea", "pfs", "fs")),
    "study_economics": ("Study economics with price, discount rate, tax basis and effective date",
                        "financial", ["npv", "initial_capex"], ("pea", "pfs", "fs", "construction")),
    "permitting": ("Principal authorizations: status from the regulator, conditions", "environmental",
                   ["permit_status"], ("pea", "pfs", "fs", "construction", "operating")),
    "community": ("Community and Indigenous agreements, disputes and consultation record", "community",
                  [], STAGES),
    "infrastructure": ("Power, water, access and processing dependencies", "engineering", [],
                       ("pea", "pfs", "fs", "construction")),
    "management_commitments": ("Management targets versus delivery history", "governance", [], STAGES),
    "production": ("Reported production and costs against guidance", "financial", [], ("operating",)),
}


def build_checklist(store: Store, actor: Actor, company_id: str, project_id: str | None = None) -> list[dict]:
    store.get(actor, "companies", company_id)
    stage = None
    if project_id:
        p = store.get(actor, "projects", project_id)
        stage = p["stage"]
    tmpl = f"stage:{stage or 'unknown'}"
    out = []
    with store.db.tx():
        for key, (title, spec, metrics, stages) in ITEMS.items():
            if stage and stage not in stages:
                continue
            existing = store.find(actor, "diligence_items", company_id=company_id, project_id=project_id,
                                  item_key=key)
            if existing:
                out.append(existing[0])
                continue
            out.append(store.insert(actor, "diligence_items", {
                "company_id": company_id, "project_id": project_id, "template": tmpl, "item_key": key,
                "title": title, "specialist": spec, "required_metrics": metrics, "status": "open",
                "evidence": [], "notes": ""}))
    refresh(store, actor, company_id, project_id)
    return store.find(actor, "diligence_items", company_id=company_id, project_id=project_id, order="item_key")


def refresh(store: Store, actor: Actor, company_id: str, project_id: str | None = None) -> list[dict]:
    """Attach current evidence to items; open specific questions for gaps."""
    created = []
    items = store.find(actor, "diligence_items", company_id=company_id, project_id=project_id)
    for it in items:
        if it["status"] in ("reviewed", "not_applicable"):
            continue
        evidence, gaps = [], []
        for mid in it["required_metrics"]:
            facts = [f for f in store.find(actor, "facts", company_id=company_id, metric_id=mid)
                     if f["workflow_state"] in ("source_matched", "needs_review", "reviewer_approved", "conflicting")
                     and (project_id is None or f["project_id"] in (project_id, None))]
            if facts:
                evidence.extend(f["id"] for f in facts)
            else:
                gaps.append(mid)
        status = "evidence_attached" if evidence and not gaps else "open"
        store.update(actor, "diligence_items", it["id"], {"evidence": evidence, "status": status})
        for mid in gaps:
            key = f"gap:{company_id}:{project_id}:{it['item_key']}:{mid}"
            if store.db.one("SELECT 1 FROM diligence_questions WHERE tenant_id=? AND dedupe_key=?",
                            (store.scope(actor), key)):
                continue
            created.append(store.insert(actor, "diligence_questions", {
                "company_id": company_id, "project_id": project_id, "item_id": it["id"],
                "question": f"Not found in documents reviewed: {mid.replace('_', ' ')}. "
                            f"Which primary document establishes it, and as of what date?",
                "specialist": it["specialist"], "document_request": _doc_request(mid),
                "status": "open", "origin": "rule:missing_required_metric", "dedupe_key": key,
                "created_by": actor.user_id, "created_at": config.iso_now()}))
    return created


def _doc_request(metric_id: str) -> str:
    return {
        "ownership_interest": "Property agreements and the latest annual information form",
        "shares_outstanding_basic": "Latest financial statements / MD&A capital-structure note",
        "cash_unrestricted": "Latest interim financial statements",
        "total_debt": "Latest interim financial statements (borrowings note)",
        "period_cash_outflow": "Latest interim cash-flow statement",
        "resource_contained_metal": "Current technical report (resource chapter)",
        "reserve_contained_metal": "Current feasibility-level technical report",
        "met_test_recovery": "Metallurgical testwork reports",
        "npv": "Current technical report (economic analysis chapter)",
        "initial_capex": "Current technical report (capital cost chapter)",
        "permit_status": "Regulator registry record and permit documents",
    }.get(metric_id, "Primary source document")


def add_question(store: Store, actor: Actor, company_id: str, question: str, specialist: str = "",
                 document_request: str = "", project_id: str | None = None, item_id: str | None = None) -> dict:
    return store.insert(actor, "diligence_questions", {
        "company_id": company_id, "project_id": project_id, "item_id": item_id, "question": question,
        "specialist": specialist, "document_request": document_request, "status": "open",
        "origin": "analyst", "dedupe_key": None, "created_by": actor.user_id, "created_at": config.iso_now()})


def review_item(store: Store, actor: Actor, item_id: str, notes: str) -> None:
    if not actor.can("review"):
        raise AccessDenied("checklist items are marked reviewed by a reviewer")
    store.update(actor, "diligence_items", item_id, {"status": "reviewed", "notes": notes,
                                                     "reviewed_by": actor.user_id,
                                                     "reviewed_at": config.iso_now()})
    store.audit(actor, "diligence_item_reviewed", item_id)


def checklist_status_label(items: list[dict]) -> str:
    """Describes what was done. Never 'complete diligence'."""
    if not items:
        return "No checklist created"
    open_n = sum(1 for i in items if i["status"] in ("open", "evidence_attached"))
    if open_n:
        return f"{open_n} of {len(items)} checklist items not yet reviewed"
    who = sorted({i["reviewed_by"] for i in items if i["reviewed_by"]})
    last = max((i["reviewed_at"] or "" for i in items), default="")
    return (f"All {len(items)} checklist items reviewed by {', '.join(who)} (latest {last[:10]}). "
            "This records the review performed; it is not a certification that diligence is complete.")


# ------------------------------------------------------------------ commitments
def _tokens(s: str) -> set:
    stop = {"the", "a", "an", "to", "of", "in", "its", "and", "for", "on", "by"}
    return {w for w in re.findall(r"[a-z0-9-]+", s.lower()) if w not in stop}


def record_commitment(store: Store, actor: Actor, company_id: str, cand, location_id: str,
                      project_id: str | None, version_id: str) -> dict:
    """Capture an attributed, conditional management statement — or link a revision."""
    from .quantities import target_window
    start, end, note = target_window(cand.target_text)
    if cand.is_revision:
        best, overlap = None, 0.0
        for c in store.find(actor, "commitments", company_id=company_id):
            a, b = _tokens(c["subject"]), _tokens(cand.subject)
            j = len(a & b) / max(1, len(a | b))
            if j > overlap:
                best, overlap = c, j
        if best and overlap >= 0.5:
            store.insert(actor, "commitment_updates", {
                "commitment_id": best["id"], "kind": "explicit_revision", "wording": cand.wording,
                "location_id": location_id, "new_target_text": cand.target_text, "new_window_end": end,
                "stated_on": cand.stated_on, "created_at": config.iso_now()})
            store.update(actor, "commitments", best["id"], {"status": "revised"})
            events.emit(store, actor, "commitment_revised",
                        f"Target explicitly revised: {best['subject']} — {best['target_text']} → {cand.target_text}",
                        company_id=company_id, project_id=project_id, source_version_id=version_id,
                        detail={"previous": best["target_text"], "new": cand.target_text,
                                "wording": cand.wording},
                        links=[("commitment", best["id"])])
            from . import monitoring
            monitoring.on_commitment_revised(
                store, actor, best["id"], company_id,
                f"management target '{best['subject']}' explicitly revised from {best['target_text']} "
                f"to {cand.target_text}")
            return best
    if cand.wording and any(c["original_wording"] == cand.wording
                            for c in store.find(actor, "commitments", company_id=company_id)):
        return next(c for c in store.find(actor, "commitments", company_id=company_id)
                    if c["original_wording"] == cand.wording)
    row = store.insert(actor, "commitments", {
        "company_id": company_id, "project_id": project_id, "original_wording": cand.wording,
        "attribution": "issuer_management", "stated_on": cand.stated_on, "location_id": location_id,
        "subject": cand.subject, "target_text": cand.target_text, "target_window_start": start,
        "target_window_end": end, "window_note": note, "conditions": "", "status": "pending",
        "created_at": config.iso_now()})
    events.emit(store, actor, "commitment_recorded", f"Management target recorded: {cand.subject} ({cand.target_text})",
                company_id=company_id, project_id=project_id, source_version_id=version_id,
                links=[("commitment", row["id"])], notify=False)
    return row


def commitment_view(store: Store, actor: Actor, company_id: str) -> list[dict]:
    """Status is described from evidence; a passed target is not called 'missed'."""
    store.get(actor, "companies", company_id)
    today = config.today().isoformat()
    out = []
    for c in store.find(actor, "commitments", company_id=company_id, order="stated_on"):
        c["updates"] = store.find(actor, "commitment_updates", commitment_id=c["id"], order="created_at")
        latest_end = c["updates"][-1]["new_window_end"] if c["updates"] else c["target_window_end"]
        if c["status"] in ("pending", "revised") and latest_end and latest_end < today:
            c["display_status"] = ("Target window has passed; no completion or revision disclosed in "
                                   "documents reviewed (this is an observation, not a finding of a missed target)")
        elif c["status"] == "revised":
            c["display_status"] = "Explicitly revised by the issuer"
        else:
            c["display_status"] = {"pending": "Pending — target window open", "met": "Completion disclosed",
                                   "withdrawn": "Withdrawn by the issuer"}.get(c["status"], c["status"])
        out.append(c)
    return out


def mark_commitment(store: Store, actor: Actor, commitment_id: str, kind: str, wording: str,
                    location_id: str) -> None:
    if kind not in ("completion", "reaffirmation", "withdrawal"):
        raise Invalid("kind must be completion, reaffirmation or withdrawal")
    store.get(actor, "source_locations", location_id)
    store.insert(actor, "commitment_updates", {"commitment_id": commitment_id, "kind": kind, "wording": wording,
                                               "location_id": location_id, "created_at": config.iso_now()})
    status = {"completion": "met", "withdrawal": "withdrawn"}.get(kind)
    if status:
        store.update(actor, "commitments", commitment_id, {"status": status})
