"""Monitoring & portfolio: coverage status, change inbox, thesis-assumption
links, watchlists, holdings and exposures.

Coverage status describes the EVIDENCE BASE (fresh, stale, incomplete,
ingestion failed). It is not a judgement about the company. An ingestion
outage must never make stale information look current, so every status
carries its reasons and dates.
"""

from __future__ import annotations

from datetime import date

from . import calc, config, entities, events
from . import definitions as D
from .auth import Actor
from .store import Invalid, Store

CONNECTORS = [
    ("SEDAR+ filings connector", "Not built. Access terms for automated retrieval not yet reviewed; "
     "uploads of filings obtained lawfully are supported."),
    ("SEC EDGAR connector", "Not built in this product. EDGAR permits automated access with a declared "
     "User-Agent and rate limits; a connector is a next integration task."),
    ("Market-data vendor feed", "Not configured: requires a licensed vendor and redistribution rights. "
     "Market data enters only as uploaded files with a stated source."),
    ("Regulator permit registries", "Not configured: jurisdiction-specific; status must be confirmed from "
     "the official record."),
    ("Insider-transaction data", "Not configured: requires licensed or official source (e.g. SEDI)."),
]


def seed_feeds(store: Store, actor: Actor) -> None:
    have = {f["name"] for f in store.find(actor, "source_feeds")}
    for name, note in CONNECTORS:
        if name not in have:
            store.insert(actor, "source_feeds", {"name": name, "kind": "connector", "status": "not_configured",
                                                 "licensing_note": note, "refresh_expectation_days": None})


# ------------------------------------------------------------------ hooks from ingestion/review
def on_new_fact(store: Store, actor: Actor, fact: dict) -> None:
    """Link a new fact to thesis assumptions that depend on its metric."""
    if fact["workflow_state"] not in D.CURRENT_STATES:
        return
    for a in store.find(actor, "thesis_assumptions", company_id=fact["company_id"]):
        if fact["metric_id"] not in a["metric_ids"]:
            continue
        if a["project_id"] and fact["project_id"] and a["project_id"] != fact["project_id"]:
            continue
        if fact["id"] in a["fact_ids"]:
            continue
        reason = (f"new {D.metric(fact['metric_id']).label.lower()} disclosed "
                  f"({fact['raw_value']}, {fact['as_of_date'] or fact['effective_date'] or 'undated'}); "
                  "assumption needs re-review")
        store.update(actor, "thesis_assumptions", a["id"], {"status": "affected_by_change", "status_reason": reason,
                                                            "updated_at": config.iso_now()})
        ev = events.emit(store, actor, "thesis_assumption_affected", f"Thesis assumption affected: {a['text'][:90]}",
                         company_id=fact["company_id"], project_id=fact["project_id"],
                         source_version_id=fact["version_id"], detail={"reason": reason},
                         dedupe_key=f"assumption:{a['id']}:{fact['version_id']}",
                         links=[("thesis_assumption", a["id"]), ("fact", fact["id"])])
        store.db.execute("INSERT OR IGNORE INTO event_links(tenant_id,event_id,kind,target_id) VALUES(?,?,?,?)",
                         (store.scope(actor), ev["id"], "fact", fact["id"]))


def on_fact_approved(store: Store, actor: Actor, fact: dict) -> None:
    from . import diligence
    for it in store.find(actor, "diligence_items", company_id=fact["company_id"]):
        diligence.refresh(store, actor, fact["company_id"], it["project_id"])
        break


def on_commitment_revised(store: Store, actor: Actor, commitment_id: str, company_id: str, reason: str) -> None:
    for a in store.find(actor, "thesis_assumptions", company_id=company_id):
        if commitment_id in a["commitment_ids"]:
            store.update(actor, "thesis_assumptions", a["id"], {"status": "affected_by_change",
                                                                "status_reason": reason,
                                                                "updated_at": config.iso_now()})
            events.emit(store, actor, "thesis_assumption_affected", f"Thesis assumption affected: {a['text'][:90]}",
                        company_id=company_id, detail={"reason": reason},
                        links=[("thesis_assumption", a["id"]), ("commitment", commitment_id)])


# ------------------------------------------------------------------ coverage status
def coverage_status(store: Store, actor: Actor, company_id: str) -> dict:
    from . import ingest
    cov = ingest.coverage(store, actor, company_id)
    s = store.settings
    today = config.today()
    statuses, reasons = [], []
    if cov["ingestion_failed"]:
        statuses.append("ingestion_failed")
        reasons.append(f"{len(cov['ingestion_failed'])} document(s) failed ingestion: "
                       + "; ".join(x["title"] for x in cov["ingestion_failed"]))
    if cov["unreadable_pages"]:
        statuses.append("incomplete")
        reasons.append("unreadable pages not reviewed: " + "; ".join(
            f"{x['title']} p.{','.join(map(str, x['pages']))}" for x in cov["unreadable_pages"]))
    gaps = [q for q in store.find(actor, "diligence_questions", company_id=company_id, status="open")
            if q["origin"] == "rule:missing_required_metric"]
    if gaps:
        if "incomplete" not in statuses:
            statuses.append("incomplete")
        reasons.append(f"{len(gaps)} required item(s) not found in documents reviewed")
    if not cov["documents_reviewed"]:
        statuses.append("incomplete")
        reasons.append("no documents reviewed")
    disclosures = [d["publication_date"] for d in cov["documents_reviewed"]
                   if d["publication_date"] and d["doc_type"] != "market_data"]
    if disclosures:
        newest = max(disclosures)
        age = (today - date.fromisoformat(newest)).days
        if age > s.freshness_days:
            statuses.append("stale")
            reasons.append(f"newest company disclosure reviewed is dated {newest} ({age} days old; "
                           f"threshold {s.freshness_days})")
    elif cov["documents_reviewed"]:
        statuses.append("incomplete")
        reasons.append("no company disclosure documents reviewed (market data only)")
    price = None
    for f in store.find(actor, "facts", company_id=company_id, metric_id="share_price"):
        if f["workflow_state"] in D.CURRENT_STATES and (price is None or (f["as_of_date"] or "") > (price["as_of_date"] or "")):
            price = f
    if price and price["as_of_date"]:
        age = (today - date.fromisoformat(price["as_of_date"])).days
        if age > s.market_data_stale_days:
            statuses.append("stale")
            reasons.append(f"market data dated {price['as_of_date']} ({age} days old)")
    elif not price:
        reasons.append("no market data uploaded")
    failed_feed = [f for f in store.find(actor, "source_feeds", status="failed")]
    if failed_feed:
        statuses.append("ingestion_failed")
        reasons.append("source feed failure: " + "; ".join(f"{f['name']} ({f['last_error'][:80]})" for f in failed_feed))
    order = ["ingestion_failed", "incomplete", "stale"]
    primary = next((x for x in order if x in statuses), "fresh")
    return {"status": primary, "all": sorted(set(statuses)) or ["fresh"], "reasons": reasons,
            "evidence_cutoff": cov["evidence_cutoff"], "analysis_time": cov["analysis_time"], "coverage": cov}


# ------------------------------------------------------------------ watchlists & inbox
def create_watchlist(store: Store, actor: Actor, name: str) -> dict:
    return store.insert(actor, "watchlists", {"name": name, "created_by": actor.user_id,
                                              "created_at": config.iso_now()})


def watch(store: Store, actor: Actor, watchlist_id: str, company_id: str) -> None:
    tenant = store.require(actor, "write")
    store.get(actor, "watchlists", watchlist_id)
    store.get(actor, "companies", company_id)
    store.db.execute("INSERT OR IGNORE INTO watchlist_members(tenant_id,watchlist_id,company_id,added_at) "
                     "VALUES(?,?,?,?)", (tenant, watchlist_id, company_id, config.iso_now()))


def watchlist_view(store: Store, actor: Actor, watchlist_id: str | None = None) -> list[dict]:
    tenant = store.require(actor, "read")
    if watchlist_id:
        store.get(actor, "watchlists", watchlist_id)
        ids = [r["company_id"] for r in store.db.all(
            "SELECT company_id FROM watchlist_members WHERE tenant_id=? AND watchlist_id=?", (tenant, watchlist_id))]
        companies = [store.get(actor, "companies", i) for i in ids]
    else:
        companies = store.find(actor, "companies")
    out = []
    for c in sorted(companies, key=lambda c: c["name"]):
        cs = coverage_status(store, actor, c["id"])
        new_events = store.find(actor, "events", company_id=c["id"], status="new")
        out.append({"company": c, "status": cs["status"], "statuses": cs["all"], "reasons": cs["reasons"],
                    "evidence_cutoff": cs["evidence_cutoff"], "new_events": len(new_events),
                    "projects": entities.projects_of(store, actor, c["id"])})
    return out


def inbox(store: Store, actor: Actor, company_id: str | None = None, include_closed: bool = False) -> list[dict]:
    if company_id:
        store.get(actor, "companies", company_id)
    where = {"company_id": company_id} if company_id else {}
    rows = store.find(actor, "events", order="created_at DESC", **where)
    if not include_closed:
        rows = [r for r in rows if r["status"] == "new"]
    for r in rows:
        r["links"] = events.links_of(store, actor, r["id"])
    return rows


def notifications(store: Store, actor: Actor, unread_only: bool = True) -> list[dict]:
    rows = store.find(actor, "notifications", order="created_at DESC", limit=200)
    rows = [r for r in rows if r["user_id"] in (None, actor.user_id)]
    return [r for r in rows if not r["read_at"]] if unread_only else rows


# ------------------------------------------------------------------ portfolio
def add_holding(store: Store, actor: Actor, portfolio: str, company_id: str, shares: str, as_of_date: str) -> dict:
    store.get(actor, "companies", company_id)
    from decimal import Decimal
    if Decimal(str(shares)) <= 0:
        raise Invalid("shares must be positive")
    return store.insert(actor, "holdings", {"portfolio": portfolio, "company_id": company_id, "shares": str(shares),
                                            "as_of_date": as_of_date, "created_by": actor.user_id,
                                            "created_at": config.iso_now()})


def exposures(store: Store, actor: Actor, portfolio: str) -> dict:
    """Shared dependencies that are SUPPORTED by records. Unknowns are listed,
    never filled in, so the view cannot imply complete coverage."""
    holds = store.find(actor, "holdings", portfolio=portfolio)
    groups = {"commodity": {}, "jurisdiction": {}, "stage": {}, "counterparty": {}, "funding_dependency": {}}
    unknown = []
    liquidity = []
    for h in holds:
        c = store.get(actor, "companies", h["company_id"])
        projs = entities.projects_of(store, actor, c["id"])
        if not projs:
            unknown.append(f"{c['name']}: no projects recorded — commodity/jurisdiction/stage exposure not established")
        for p in projs:
            for dim, val in (("commodity", p["commodity"]), ("jurisdiction", p["jurisdiction"]),
                             ("stage", D.STAGE_LABELS.get(p["stage"] or "", None))):
                if val:
                    groups[dim].setdefault(val, []).append(f"{c['name']} — {p['name']}")
                else:
                    unknown.append(f"{c['name']} — {p['name']}: {dim} not recorded")
        links = store.find(actor, "counterparty_links", company_id=c["id"])
        if links:
            for l in links:
                cp = store.get(actor, "counterparties", l["counterparty_id"])
                groups["counterparty"].setdefault(f"{cp['name']} ({l['relation']})", []).append(c["name"])
        else:
            unknown.append(f"{c['name']}: counterparties not established in documents reviewed")
        gc = [f for f in store.find(actor, "facts", company_id=c["id"], metric_id="disclosure_signal")
              if f["normalized_value"] == "going_concern" and f["workflow_state"] in D.CURRENT_STATES]
        if gc:
            groups["funding_dependency"].setdefault("Going-concern material uncertainty disclosed", []).append(
                f"{c['name']} ({gc[0]['as_of_date']})")
        rw = calc.runway(store, actor, c["id"])
        if rw.status == "computed":
            groups["funding_dependency"].setdefault("Runway scenario computed (from cash date)", []).append(
                f"{c['name']}: {rw.display()} from {rw.parameters['cash_date']}")
        else:
            unknown.append(f"{c['name']}: runway withheld — {'; '.join(rw.missing)}")
        lq = calc.liquidity_days(store, actor, c["id"], h["shares"])
        liquidity.append({"company": c["name"], "shares": h["shares"], "status": lq.status,
                          "table": lq.parameters.get("table"), "missing": lq.missing,
                          "adv_date": lq.parameters.get("adv_date"), "caveats": lq.caveats})
    return {"portfolio": portfolio, "holdings": holds, "groups": groups, "not_established": unknown,
            "liquidity": liquidity,
            "note": "Only exposures supported by recorded facts are shown. Items under 'not established' are "
                    "unknown, not absent."}
