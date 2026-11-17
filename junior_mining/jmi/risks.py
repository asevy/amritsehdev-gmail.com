"""Integrated risk register (brief §9).

Each finding has a neutral title, affected company/project, dated supporting
evidence, contrary evidence, potential consequence, dependencies, mitigants,
unresolved questions, a monitoring trigger, an owner and reviewer, a status
and a full history.

There are no risk scores and no high/medium/low grades. An analyst may mark
an item as requiring attention and must say why. Rules may OPEN QUESTIONS from
documented disclosures; only an analyst, confirmed by a reviewer, can turn a
question into a documented finding. Nothing here labels fraud or misconduct,
and nothing infers management quality from tone.
"""

from __future__ import annotations

from . import config
from .auth import Actor
from .definitions import RISK_CATEGORIES, RISK_STATUSES
from .store import AccessDenied, Invalid, Store

FIELDS = ("title", "consequence", "dependencies_text", "mitigants", "unresolved_questions",
          "monitoring_trigger", "owner", "reviewer", "project_id", "category")


def _history(store, actor, risk_id, change: dict) -> None:
    store.insert(actor, "risk_history", {"risk_id": risk_id, "actor": actor.user_id,
                                         "at": config.iso_now(), "change": change})


def create(store: Store, actor: Actor, company_id: str, category: str, title: str, *,
           project_id: str | None = None, consequence: str = "", dependencies_text: str = "",
           mitigants: str = "", unresolved_questions: str = "", monitoring_trigger: str = "",
           owner: str = "", reviewer: str = "", origin: str = "analyst", dedupe: bool = False) -> dict:
    if category not in RISK_CATEGORIES:
        raise Invalid(f"category must be one of {', '.join(RISK_CATEGORIES)}")
    store.get(actor, "companies", company_id)
    if dedupe:
        prior = store.find(actor, "risk_findings", company_id=company_id, origin=origin)
        if prior:
            return prior[0]
    now = config.iso_now()
    with store.db.tx():
        r = store.insert(actor, "risk_findings", {
            "company_id": company_id, "project_id": project_id, "category": category, "title": title,
            "consequence": consequence, "dependencies_text": dependencies_text, "mitigants": mitigants,
            "unresolved_questions": unresolved_questions, "monitoring_trigger": monitoring_trigger,
            "owner": owner or actor.user_id, "reviewer": reviewer, "status": "open_question",
            "attention": 0, "attention_reason": "", "origin": origin, "created_by": actor.user_id,
            "created_at": now, "updated_at": now})
        _history(store, actor, r["id"], {"created": {"status": "open_question", "origin": origin}})
        store.audit(actor, "risk_created", r["id"], origin)
    return r


def add_evidence(store: Store, actor: Actor, risk_id: str, stance: str, *, fact_id: str | None = None,
                 location_id: str | None = None, note: str = "") -> dict:
    if stance not in ("supporting", "contrary"):
        raise Invalid("stance must be supporting or contrary")
    if not fact_id and not location_id:
        raise Invalid("evidence must cite a fact or a source location")
    store.get(actor, "risk_findings", risk_id)
    ev_date = None
    if fact_id:
        f = store.get(actor, "facts", fact_id)
        ev_date = f["as_of_date"] or f["effective_date"] or f["publication_date"]
        location_id = location_id or f["location_id"]
    if location_id:
        loc = store.get(actor, "source_locations", location_id)
        if not ev_date:
            v = store.get(actor, "document_versions", loc["version_id"])
            ev_date = v["publication_date"]
    with store.db.tx():
        row = store.insert(actor, "risk_evidence", {
            "risk_id": risk_id, "stance": stance, "fact_id": fact_id, "location_id": location_id,
            "note": note, "evidence_date": ev_date, "added_by": actor.user_id, "added_at": config.iso_now()})
        _history(store, actor, risk_id, {"evidence_added": {"stance": stance, "fact_id": fact_id,
                                                            "location_id": location_id}})
        from . import lineage
        if fact_id:
            lineage.link(store, actor, "fact", fact_id, "risk", risk_id)
    return row


def update(store: Store, actor: Actor, risk_id: str, patch: dict) -> None:
    bad = set(patch) - set(FIELDS)
    if bad:
        raise Invalid(f"not editable here: {sorted(bad)}")
    if "category" in patch and patch["category"] not in RISK_CATEGORIES:
        raise Invalid("unknown category")
    before = store.get(actor, "risk_findings", risk_id)
    with store.db.tx():
        store.update(actor, "risk_findings", risk_id, {**patch, "updated_at": config.iso_now()})
        _history(store, actor, risk_id, {k: {"from": before.get(k), "to": v} for k, v in patch.items()})


def set_attention(store: Store, actor: Actor, risk_id: str, attention: bool, reason: str) -> None:
    """Analyst judgement, recorded with its reason. Not a grade."""
    if attention and not reason.strip():
        raise Invalid("marking an item as requiring attention requires a reason")
    with store.db.tx():
        store.update(actor, "risk_findings", risk_id, {"attention": 1 if attention else 0,
                                                       "attention_reason": reason.strip(),
                                                       "updated_at": config.iso_now()})
        _history(store, actor, risk_id, {"attention": {"to": bool(attention), "reason": reason}})


def set_status(store: Store, actor: Actor, risk_id: str, status: str, reason: str) -> None:
    if status not in RISK_STATUSES:
        raise Invalid(f"status must be one of {', '.join(RISK_STATUSES)}")
    r = store.get(actor, "risk_findings", risk_id)
    if status == "documented_finding":
        if not actor.can("review"):
            raise AccessDenied("a documented finding requires reviewer confirmation")
        ev = store.find(actor, "risk_evidence", risk_id=risk_id, stance="supporting")
        if not ev:
            raise Invalid("a documented finding needs at least one cited supporting source")
        if r["created_by"] == actor.user_id and r["origin"] == "analyst":
            raise AccessDenied("the reviewer confirming a finding must not be its author")
    if status in ("dismissed", "resolved", "mitigated") and not reason.strip():
        raise Invalid(f"status '{status}' requires a reason")
    with store.db.tx():
        store.update(actor, "risk_findings", risk_id, {"status": status, "updated_at": config.iso_now(),
                                                       **({"reviewer": actor.user_id}
                                                          if status == "documented_finding" else {})})
        _history(store, actor, risk_id, {"status": {"from": r["status"], "to": status, "reason": reason}})
        store.audit(actor, "risk_status", risk_id, f"{r['status']}->{status}")


def register(store: Store, actor: Actor, company_id: str | None = None) -> list[dict]:
    if company_id:
        store.get(actor, "companies", company_id)
    rows = store.find(actor, "risk_findings", **({"company_id": company_id} if company_id else {}),
                      order="category, created_at")
    for r in rows:
        r["evidence"] = store.find(actor, "risk_evidence", risk_id=r["id"], order="evidence_date")
        r["history"] = store.find(actor, "risk_history", risk_id=r["id"], order="at")
    return rows


# ------------------------------------------------------------------ rule suggestions
def suggest_from_fact(store: Store, actor: Actor, fact: dict) -> list[dict]:
    """Open QUESTIONS (never findings) prompted by specific documented disclosures."""
    out = []
    m, cid, pid = fact["metric_id"], fact["company_id"], fact.get("project_id")
    if fact["workflow_state"] == "rejected":
        return out

    def q(rule, category, title, **kw):
        r = create(store, actor, cid, category, title, project_id=pid, origin=f"rule:{rule}", dedupe=True, **kw)
        if not store.find(actor, "risk_evidence", risk_id=r["id"], fact_id=fact["id"]):
            add_evidence(store, actor, r["id"], "supporting", fact_id=fact["id"],
                         note="disclosure that prompted this question")
        out.append(r)

    if m == "disclosure_signal" and fact["normalized_value"] == "going_concern":
        q("going_concern", "financing_shareholder",
          "Issuer discloses a material uncertainty about its ability to continue as a going concern",
          consequence="Funding may be required on terms that dilute existing holders.",
          unresolved_questions="Committed financing? Current (not dated) cash? Planned spend?",
          monitoring_trigger="Next quarterly filing; any financing announcement.")
    elif m == "disclosure_signal":
        q(f"signal_{fact['normalized_value']}", "evidence_quality",
          f"Disclosure noted: {fact['qualifiers'].get('label', fact['normalized_value'])}",
          unresolved_questions="Obtain the underlying filing section and auditor communication.")
    elif m == "permit_status" and fact["normalized_value"] in ("applied", "accepted_for_review",
                                                                 "conditional_approval"):
        q("permit_not_issued", "permitting_environment",
          f"{fact['qualifiers'].get('permit', 'Authorization')}: not issued in documents reviewed",
          consequence="Development schedule depends on a decision not yet made.",
          dependencies_text="Regulator decision; any conditions attached.",
          unresolved_questions="Confirm status in the official registry (primary source).",
          monitoring_trigger="Regulator decision or registry update.")
    elif m == "npv" and fact.get("study_type") == "pea":
        q("pea_economics", "engineering_construction",
          "Project economics are from a PEA (preliminary; may rely on Inferred resources)",
          consequence="Economics may change materially at pre-feasibility or feasibility level.",
          unresolved_questions="Share of mine plan from Inferred? Capital cost basis and contingency?")
    elif m == "warrants_outstanding":
        q("warrant_overhang", "financing_shareholder",
          "Warrants outstanding: potential dilution if exercised",
          consequence="Additional shares on exercise; proceeds are hypothetical until exercised.",
          monitoring_trigger="Share price relative to exercise price; expiry date.")
    elif m == "historical_estimate_contained_metal":
        q("historical_estimate", "evidence_quality",
          "A historical estimate is disclosed; it is not a current mineral resource",
          unresolved_questions="Has a qualified person verified any of it? Is a current estimate planned?")
    return out
