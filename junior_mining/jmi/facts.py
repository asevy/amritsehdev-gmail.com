"""Fact lifecycle: insertion, reconciliation, review, correction, retrieval.

Reconciliation compares only EQUIVALENT metrics (same definition, entity,
category, basis, study qualifiers and date — the equivalence key). Two
reports of the same key reconcile when their printed-precision intervals
overlap; otherwise both are marked conflicting and a discrepancy is opened.
A newer document does NOT supersede every older fact: only an explicit
restatement of the same key, or a reviewer correction, supersedes — and the
superseded row is preserved with its lineage.
"""

from __future__ import annotations

from decimal import Decimal

from . import config, events, lineage
from . import definitions as D
from .auth import Actor
from .db import dumps
from .quantities import METAL, MASS, interval, overlaps, parse_number, scale_exp
from .store import AccessDenied, Invalid, NotFound, Store


def _transition(fact: dict, to_state: str) -> None:
    if to_state not in D.TRANSITIONS.get(fact["workflow_state"], set()):
        raise Invalid(f"cannot move a fact from '{fact['workflow_state']}' to '{to_state}'")


def _decide(store, actor, fact, to_state, decision, reason) -> None:
    _transition(fact, to_state)
    store.update(actor, "facts", fact["id"], {"workflow_state": to_state, "updated_at": config.iso_now()})
    store.insert(actor, "review_decisions", {
        "target_kind": "fact", "target_id": fact["id"], "decision": decision,
        "from_state": fact["workflow_state"], "to_state": to_state, "reason": reason,
        "actor": actor.user_id, "at": config.iso_now()})
    store.audit(actor, f"fact_{decision}", fact["id"], f"{fact['workflow_state']}->{to_state}")


def consistent(a: dict, b: dict) -> bool:
    if a["value_kind"] != "decimal" or b["value_kind"] != "decimal":
        return a["normalized_value"] == b["normalized_value"]
    if a["normalized_value"] is None or b["normalized_value"] is None:
        return True        # unknown is not a conflicting value
    ia = (Decimal(a["precision_lo"]), Decimal(a["precision_hi"])) if a["precision_lo"] else \
        (Decimal(a["normalized_value"]),) * 2
    ib = (Decimal(b["precision_lo"]), Decimal(b["precision_hi"])) if b["precision_lo"] else \
        (Decimal(b["normalized_value"]),) * 2
    if a.get("currency") and b.get("currency") and a["currency"] != b["currency"]:
        return False
    return overlaps(ia, ib)


def insert_fact(store: Store, actor: Actor, *, cand, val, version: dict, location_id: str,
                run_id: str | None, extractor: str, extractor_version: str) -> dict:
    d = D.metric(cand.metric_id)
    now = config.iso_now()
    prior = [f for f in store.find(actor, "facts", equivalence_key=val.equivalence_key)
             if f["workflow_state"] in D.CURRENT_STATES]
    restating = (cand.qualifiers.get("relation_hint") == "restatement" and val.state != "rejected"
                 and any(p["version_id"] != version["id"] for p in prior))
    revision_of = None
    if restating:
        revision_of = sorted(prior, key=lambda p: p["created_at"])[-1]["id"]
    f = val.fields
    row = store.insert(actor, "facts", {
        "company_id": val.company_id, "project_id": val.project_id, "metric_id": cand.metric_id,
        "definition_version": d.version, "raw_text": cand.quote, "raw_value": cand.raw_value,
        "normalized_value": val.normalized_value, "value_kind": val.value_kind, "unit": val.unit,
        "currency": val.currency,
        "precision_lo": str(val.precision[0]) if val.precision else None,
        "precision_hi": str(val.precision[1]) if val.precision else None,
        "transformations": val.transformations, "scope_basis": f.get("scope_basis"),
        "period_start": f.get("period_start"), "period_end": f.get("period_end"),
        "as_of_date": f.get("as_of_date"), "effective_date": f.get("effective_date"),
        "publication_date": version.get("publication_date"), "retrieved_at": version.get("retrieved_at"),
        "study_type": f.get("study_type"), "tax_basis": f.get("tax_basis"),
        "discount_rate": f.get("discount_rate"), "resource_category": f.get("resource_category"),
        "reporting_basis": f.get("reporting_basis"), "estimate_status": f.get("estimate_status"),
        "qualifiers": val.qualifiers, "attribution": val.attribution, "evidence_type": val.evidence_type,
        "workflow_state": val.state, "checks": val.checks, "missing_reason": val.missing_reason,
        "version_id": version["id"], "location_id": location_id, "equivalence_key": val.equivalence_key,
        "revision_of": revision_of, "relation": "restatement" if restating else None,
        "extractor": extractor, "extractor_version": extractor_version, "ingestion_run_id": run_id,
        "created_by": actor.user_id, "created_at": now, "updated_at": now})
    lineage.link(store, actor, "location", location_id, "fact", row["id"])
    row = store.get(actor, "facts", row["id"])
    if val.state == "rejected" or not val.company_id:
        return row
    if restating:
        for p in prior:
            if p["version_id"] == version["id"]:
                continue
            _decide(store, actor, p, "superseded", "superseded_by_restatement",
                    f"restated in '{version['filename']}' (fact {row['id']})")
            affected = lineage.invalidate(store, actor, "fact", p["id"],
                                          f"source fact {p['id']} restated by fact {row['id']}")
            store.insert(actor, "discrepancies", {
                "company_id": row["company_id"], "kind": "restatement", "fact_a": p["id"], "fact_b": row["id"],
                "detail": f"{D.metric(p['metric_id']).label}: {p['raw_value']} restated to {row['raw_value']}",
                "status": "open", "created_at": now})
            events.emit(store, actor, "restatement",
                        f"Restated: {D.metric(p['metric_id']).label} "
                        f"({D.CATEGORY_LABELS.get(p['resource_category'] or '', '')} {p['effective_date'] or ''}) "
                        f"{p['raw_value']} → {row['raw_value']}",
                        company_id=row["company_id"], project_id=row["project_id"],
                        source_version_id=version["id"],
                        detail={"old_fact": p["id"], "new_fact": row["id"], "affected": affected},
                        links=[("fact", p["id"]), ("fact", row["id"])] +
                              [(a["kind"], a["id"]) for a in affected])
        return store.get(actor, "facts", row["id"])
    for p in prior:
        if consistent(p, row):
            continue
        for x in (p, row):
            x = store.get(actor, "facts", x["id"])
            if x["workflow_state"] != "conflicting" and "conflicting" in D.TRANSITIONS[x["workflow_state"]]:
                _decide(store, actor, x, "conflicting", "conflict_detected",
                        "another source reports a different value for the same defined metric")
                if x["workflow_state"] == "reviewer_approved":
                    lineage.invalidate(store, actor, "fact", x["id"], "a conflicting report was ingested")
        disc = store.insert(actor, "discrepancies", {
            "company_id": row["company_id"], "kind": "value_conflict", "fact_a": p["id"], "fact_b": row["id"],
            "detail": f"{D.metric(row['metric_id']).label}: '{p['raw_value']}' vs '{row['raw_value']}'",
            "status": "open", "created_at": now})
        events.emit(store, actor, "discrepancy",
                    f"Conflicting reports: {D.metric(row['metric_id']).label} '{p['raw_value']}' vs '{row['raw_value']}'",
                    company_id=row["company_id"], project_id=row["project_id"], source_version_id=version["id"],
                    detail={"discrepancy": disc["id"]}, links=[("fact", p["id"]), ("fact", row["id"])])
    return store.get(actor, "facts", row["id"])


# ------------------------------------------------------------------ review
def review(store: Store, actor: Actor, fact_id: str, decision: str, reason: str = "") -> dict:
    f = store.get(actor, "facts", fact_id)
    if decision in ("approve", "reject"):
        if not actor.can("review"):
            raise AccessDenied("only a reviewer can approve or reject a fact")
        if f["created_by"] == actor.user_id:
            raise AccessDenied("a reviewer cannot approve or reject a fact they entered or corrected")
    else:
        store.require(actor, "write")
    if decision == "approve":
        if f["workflow_state"] == "conflicting":
            raise Invalid("resolve the open discrepancy first; a conflicting fact is not approved directly")
        if f["normalized_value"] is None and f["value_kind"] == "decimal":
            raise Invalid("the value could not be read from the source; correct it (as a new revision) first")
        to, dec = "reviewer_approved", "approve"
    elif decision == "reject":
        if not reason.strip():
            raise Invalid("a rejection requires a reason")
        to, dec = "rejected", "reject"
    elif decision == "needs_review":
        to, dec = "needs_review", "request_review"
    else:
        raise Invalid("decision must be approve, reject or needs_review")
    with store.db.tx():
        was_approved = f["workflow_state"] == "reviewer_approved"
        _decide(store, actor, f, to, dec, reason)
        store.usage(actor, "reviewer_action", 1, "decision", detail=dec)
        if was_approved and to != "reviewer_approved":
            lineage.invalidate(store, actor, "fact", f["id"], f"fact {f['id']} {dec}: {reason}")
        if to == "reviewer_approved":
            from . import monitoring
            monitoring.on_fact_approved(store, actor, store.get(actor, "facts", fact_id))
    return store.get(actor, "facts", fact_id)


def resolve_discrepancy(store: Store, actor: Actor, disc_id: str, resolution: str,
                        keep_fact_id: str | None = None) -> dict:
    if not actor.can("review"):
        raise AccessDenied("discrepancies are resolved by a reviewer")
    if not resolution.strip():
        raise Invalid("a resolution must explain the decision")
    d = store.get(actor, "discrepancies", disc_id)
    with store.db.tx():
        if d["kind"] == "value_conflict" and keep_fact_id:
            if keep_fact_id not in (d["fact_a"], d["fact_b"]):
                raise Invalid("keep_fact_id must be one side of the discrepancy")
            other = d["fact_b"] if keep_fact_id == d["fact_a"] else d["fact_a"]
            k, o = store.get(actor, "facts", keep_fact_id), store.get(actor, "facts", other)
            if actor.user_id in (k["created_by"], o["created_by"]):
                raise AccessDenied("a reviewer cannot resolve a discrepancy involving their own entry")
            if o["workflow_state"] != "rejected":
                _decide(store, actor, o, "rejected", "reject", f"discrepancy {disc_id}: {resolution}")
                lineage.invalidate(store, actor, "fact", o["id"], f"rejected in discrepancy resolution")
            if k["workflow_state"] == "conflicting":
                _decide(store, actor, k, "reviewer_approved", "approve", f"discrepancy {disc_id}: {resolution}")
        store.update(actor, "discrepancies", disc_id, {"status": "resolved", "resolution": resolution,
                                                       "resolved_by": actor.user_id,
                                                       "resolved_at": config.iso_now()})
        store.audit(actor, "discrepancy_resolved", disc_id, resolution[:200])
    return store.get(actor, "discrepancies", disc_id)


def normalize(metric_id: str, raw: str, qualifiers: dict) -> tuple[str | None, tuple | None, list]:
    d = D.metric(metric_id)
    p = parse_number(raw)
    if p.value is None:
        return None, None, p.warnings
    exp = 0
    if d.dimension in ("money", "count"):
        exp = scale_exp(qualifiers.get("scale_word") or "") or 0
    elif d.dimension == "mass":
        exp = MASS.get((qualifiers.get("unit_token") or "t").lower(), ("t", 0))[1]
    elif d.dimension == "metal":
        exp = METAL.get((qualifiers.get("unit_token") or "oz").lower(), ("oz", 0))[1]
    v = p.value * Decimal(10) ** exp
    s = str(v.quantize(Decimal(1))) if v == v.to_integral_value() else str(v)
    return s, interval(v, p.decimals, exp), p.transformations


def correct_fact(store: Store, actor: Actor, fact_id: str, reason: str, *, raw_value: str | None = None,
                 project_id: str | None = None) -> dict:
    """A correction is a NEW revision. The corrected row is superseded, kept,
    and every output that used it is marked stale. A different reviewer must
    approve the revision."""
    store.require(actor, "write")
    if not reason.strip():
        raise Invalid("a correction requires a reason")
    old = store.get(actor, "facts", fact_id)
    if old["workflow_state"] in ("superseded",):
        raise Invalid("this fact is already superseded; correct the current revision")
    new = {k: old[k] for k in old if k not in ("id", "tenant_id")}
    tr = list(old["transformations"])
    if raw_value is not None and raw_value != old["raw_value"]:
        val, prec, ptr = normalize(old["metric_id"], raw_value, old["qualifiers"])
        if val is None:
            raise Invalid(f"corrected value is not a number: {raw_value}")
        tr.append(f"value corrected by {actor.user_id} from printed '{old['raw_value']}' to '{raw_value}': {reason}")
        new.update({"raw_value": raw_value, "normalized_value": val,
                    "precision_lo": str(prec[0]), "precision_hi": str(prec[1])})
    if project_id is not None and project_id != old["project_id"]:
        store.get(actor, "projects", project_id)
        tr.append(f"project assignment corrected by {actor.user_id}: {reason}")
        new["project_id"] = project_id
        from .validate import equivalence_key
        new["equivalence_key"] = equivalence_key(old["metric_id"], old["company_id"], project_id,
                                                 {k: old.get(k) for k in ("as_of_date", "effective_date",
                                                  "period_start", "period_end", "resource_category",
                                                  "scope_basis", "reporting_basis", "estimate_status",
                                                  "study_type", "tax_basis", "discount_rate")},
                                                 old["qualifiers"])
    checks = list(old["checks"]) + [{"check": "reviewer_correction", "status": "warn",
                                     "detail": f"corrected by {actor.user_id}: {reason}; requires approval "
                                               "by a different reviewer"}]
    now = config.iso_now()
    new.update({"transformations": tr, "checks": checks, "workflow_state": "needs_review",
                "revision_of": old["id"], "relation": "correction", "created_by": actor.user_id,
                "created_at": now, "updated_at": now, "missing_reason": None})
    with store.db.tx():
        row = store.insert(actor, "facts", new)
        if old["location_id"]:
            lineage.link(store, actor, "location", old["location_id"], "fact", row["id"])
        if old["workflow_state"] != "rejected":
            _decide(store, actor, old, "superseded", "superseded_by_correction", f"{reason} (fact {row['id']})")
        else:
            store.insert(actor, "review_decisions", {
                "target_kind": "fact", "target_id": old["id"], "decision": "corrected",
                "from_state": "rejected", "to_state": "rejected", "reason": f"{reason} (fact {row['id']})",
                "actor": actor.user_id, "at": now})
        affected = lineage.invalidate(store, actor, "fact", old["id"],
                                      f"source fact {old['id']} corrected (now {row['id']})")
        if affected:
            events.emit(store, actor, "outputs_invalidated",
                        f"Correction to {D.metric(old['metric_id']).label} marked {len(affected)} output(s) stale",
                        company_id=old["company_id"], project_id=old["project_id"],
                        detail={"old_fact": old["id"], "new_fact": row["id"], "affected": affected},
                        links=[("fact", old["id"]), ("fact", row["id"])] + [(a["kind"], a["id"]) for a in affected])
    return store.get(actor, "facts", row["id"])


# ------------------------------------------------------------------ retrieval
def current(store: Store, actor: Actor, company_id: str, metric_id: str | None = None,
            project_id: str | None = None, approved_only: bool = False) -> list[dict]:
    where = {"company_id": company_id}
    if metric_id:
        where["metric_id"] = metric_id
    rows = store.find(actor, "facts", **where)
    states = ("reviewer_approved",) if approved_only else D.CURRENT_STATES
    out = [r for r in rows if r["workflow_state"] in states]
    if project_id is not None:
        out = [r for r in out if r["project_id"] == project_id]
    return out


def latest(store: Store, actor: Actor, company_id: str, metric_id: str, project_id: str | None = None,
           approved_only: bool = True, on_or_before: str | None = None, **match) -> dict | None:
    """Latest-dated current fact matching qualifiers. Returns None if none —
    callers must treat None as unknown, never as zero."""
    cands = []
    for f in current(store, actor, company_id, metric_id, project_id, approved_only):
        ok = True
        for k, v in match.items():
            have = f.get(k, f["qualifiers"].get(k))
            if have != v:
                ok = False
                break
        if not ok:
            continue
        dt = f["as_of_date"] or f["effective_date"] or f["period_end"] or ""
        if on_or_before and dt and dt > on_or_before:
            continue
        cands.append((dt, f["created_at"], f))
    if not cands:
        return None
    return sorted(cands, key=lambda t: (t[0], t[1]))[-1][2]


def detail(store: Store, actor: Actor, fact_id: str) -> dict:
    f = store.get(actor, "facts", fact_id)
    loc = store.get(actor, "source_locations", f["location_id"]) if f["location_id"] else None
    ver = store.get(actor, "document_versions", f["version_id"]) if f["version_id"] else None
    doc = store.get(actor, "documents", ver["document_id"]) if ver else None
    same = [x for x in store.find(actor, "facts", equivalence_key=f["equivalence_key"]) if x["id"] != f["id"]]
    sources = []
    for x in same + [f]:
        if x["workflow_state"] not in D.CURRENT_STATES or not x["version_id"]:
            continue
        v = store.get(actor, "document_versions", x["version_id"])
        dd = store.get(actor, "documents", v["document_id"])
        sources.append({"fact_id": x["id"], "document": dd["title"], "publisher": dd["publisher"],
                        "attribution": x["attribution"], "consistent": consistent(f, x)})
    independent = sorted({s["attribution"] for s in sources if s["consistent"]
                          and s["attribution"] not in ("issuer_management", "qualified_person")})
    revisions = []
    cur = f
    while cur.get("revision_of"):
        try:
            cur = store.get(actor, "facts", cur["revision_of"])
        except NotFound:
            break
        revisions.append(cur)
    later = store.find(actor, "facts", revision_of=f["id"])
    return {"fact": f, "definition": D.metric(f["metric_id"]).as_dict(), "location": loc, "version": ver,
            "document": doc,
            "reviews": store.find(actor, "review_decisions", target_kind="fact", target_id=fact_id, order="at"),
            "earlier_revisions": revisions, "later_revisions": later,
            "dependents": [{"kind": k, "id": i} for k, i in lineage.dependents(store, actor, "fact", fact_id)],
            "sources_for_same_metric": sources,
            "corroboration_note": (
                f"Reported in {sum(1 for s in sources if s['consistent'])} current document(s). "
                f"Non-issuer sources: {len(independent)}. Repetition by the issuer, or a mirrored release, "
                "is not independent corroboration.")}
