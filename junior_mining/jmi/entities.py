"""Companies, projects, aliases, listings, ownership and counterparties.

Assets are modelled separately from issuers. Historical names, tickers and
project aliases are kept with validity dates. Ownership history is preserved:
a change closes the previous row rather than editing it. Project value,
attributable interest and corporate equity value are different quantities and
are never conflated here or in jmi/calc.py.
"""

from __future__ import annotations

from . import config
from .auth import Actor
from .definitions import STAGES
from .extract import EntityAlias
from .store import Invalid, Store


def create_company(store: Store, actor: Actor, name: str, *, legal_name: str = "",
                   incorporation: str = "", reporting_currency: str | None = None,
                   aliases: list[str] | None = None, synthetic: bool = False) -> dict:
    if not name.strip():
        raise Invalid("company name is required")
    with store.db.tx():
        row = store.insert(actor, "companies", {
            "name": name.strip(), "legal_name": legal_name or name.strip(), "incorporation": incorporation,
            "reporting_currency": reporting_currency, "synthetic": synthetic,
            "created_by": actor.user_id, "created_at": config.iso_now()})
        add_alias(store, actor, "company", row["id"], name.strip(), "name")
        for a in aliases or []:
            add_alias(store, actor, "company", row["id"], a, "former_name")
        store.audit(actor, "company_created", row["id"])
    return row


def add_alias(store: Store, actor: Actor, kind: str, entity_id: str, alias: str, alias_kind: str,
              valid_from: str | None = None, valid_to: str | None = None) -> dict:
    if kind not in ("company", "project"):
        raise Invalid("alias kind must be company or project")
    store.get(actor, "companies" if kind == "company" else "projects", entity_id)
    return store.insert(actor, "entity_aliases", {
        "entity_kind": kind, "entity_id": entity_id, "alias": alias.strip(), "alias_kind": alias_kind,
        "valid_from": valid_from, "valid_to": valid_to, "created_by": actor.user_id,
        "created_at": config.iso_now()})


def add_listing(store: Store, actor: Actor, company_id: str, exchange: str, ticker: str,
                currency: str | None = None, valid_from: str | None = None) -> dict:
    store.get(actor, "companies", company_id)
    row = store.insert(actor, "listings", {
        "company_id": company_id, "exchange": exchange.strip().upper(), "ticker": ticker.strip().upper(),
        "currency": currency, "valid_from": valid_from, "created_at": config.iso_now()})
    store.audit(actor, "listing_added", company_id, f"{exchange}:{ticker}")
    return row


def create_project(store: Store, actor: Actor, company_id: str, name: str, *, commodity: str = "",
                   jurisdiction: str = "", country: str = "", stage: str | None = None,
                   deposit_type: str = "", process_route: str = "", infrastructure: list | None = None,
                   interest_pct: str | None = None, interest_kind: str = "direct",
                   effective_date: str | None = None, aliases: list[str] | None = None,
                   synthetic: bool = False) -> dict:
    store.get(actor, "companies", company_id)
    if stage is not None and stage not in STAGES:
        raise Invalid(f"stage must be one of {', '.join(STAGES)}")
    with store.db.tx():
        p = store.insert(actor, "projects", {
            "name": name.strip(), "commodity": commodity, "jurisdiction": jurisdiction, "country": country,
            "stage": stage, "deposit_type": deposit_type, "process_route": process_route,
            "infrastructure": infrastructure or [], "synthetic": synthetic,
            "created_by": actor.user_id, "created_at": config.iso_now()})
        add_alias(store, actor, "project", p["id"], name.strip(), "name")
        for a in aliases or []:
            add_alias(store, actor, "project", p["id"], a, "project_alias")
        store.insert(actor, "ownership_interests", {
            "company_id": company_id, "project_id": p["id"], "interest_pct": interest_pct,
            "interest_kind": interest_kind, "effective_date": effective_date,
            "notes": "" if interest_pct is not None else "interest not yet established from a source",
            "created_by": actor.user_id, "created_at": config.iso_now()})
        store.audit(actor, "project_created", p["id"], f"company={company_id}")
    return p


def change_ownership(store: Store, actor: Actor, company_id: str, project_id: str, interest_pct: str,
                     effective_date: str, interest_kind: str = "direct", fact_id: str | None = None,
                     notes: str = "") -> dict:
    """Close the current interest row on effective_date and open a new one."""
    with store.db.tx():
        for r in store.find(actor, "ownership_interests", company_id=company_id, project_id=project_id,
                            end_date=None):
            store.update(actor, "ownership_interests", r["id"], {"end_date": effective_date})
        row = store.insert(actor, "ownership_interests", {
            "company_id": company_id, "project_id": project_id, "interest_pct": interest_pct,
            "interest_kind": interest_kind, "effective_date": effective_date, "fact_id": fact_id,
            "notes": notes, "created_by": actor.user_id, "created_at": config.iso_now()})
        store.audit(actor, "ownership_changed", project_id, f"{company_id} {interest_pct}% from {effective_date}")
    return row


def ownership_on(store: Store, actor: Actor, company_id: str, project_id: str,
                 on: str | None = None) -> dict | None:
    rows = store.find(actor, "ownership_interests", company_id=company_id, project_id=project_id,
                      order="effective_date")
    on = on or config.today().isoformat()
    best = None
    for r in rows:
        if (r["effective_date"] or "0000") <= on and (r["end_date"] is None or r["end_date"] > on):
            best = r
    return best


def projects_of(store: Store, actor: Actor, company_id: str, on: str | None = None) -> list[dict]:
    """Projects in which the company holds a current interest."""
    on = on or config.today().isoformat()
    out = []
    seen = set()
    for oi in store.find(actor, "ownership_interests", company_id=company_id):
        if oi["project_id"] in seen:
            continue
        if (oi["effective_date"] or "0000") <= on and (oi["end_date"] is None or oi["end_date"] > on):
            p = store.get(actor, "projects", oi["project_id"])
            p["interest"] = oi
            out.append(p)
            seen.add(oi["project_id"])
    return sorted(out, key=lambda p: p["name"])


def all_aliases(store: Store, actor: Actor) -> list[EntityAlias]:
    """Tenant-wide alias list used for entity checks during extraction."""
    out = []
    owners = {}
    for oi in store.find(actor, "ownership_interests", end_date=None):
        owners.setdefault(oi["project_id"], oi["company_id"])
    for a in store.find(actor, "entity_aliases"):
        if a["valid_to"]:
            continue
        if a["entity_kind"] == "company":
            out.append(EntityAlias("company", a["entity_id"], a["entity_id"], a["alias"]))
        else:
            out.append(EntityAlias("project", a["entity_id"], owners.get(a["entity_id"], ""), a["alias"]))
    return out


def listing_map(store: Store, actor: Actor) -> dict:
    return {f"{l['exchange']}:{l['ticker']}": l["company_id"]
            for l in store.find(actor, "listings") if not l["valid_to"]}


def add_counterparty_link(store: Store, actor: Actor, company_id: str, name: str, relation: str,
                          terms_summary: str, location_id: str | None, project_id: str | None = None,
                          synthetic: bool = False) -> dict:
    existing = [c for c in store.find(actor, "counterparties") if c["name"].lower() == name.lower()]
    cp = existing[0] if existing else store.insert(actor, "counterparties", {
        "name": name, "kind": relation, "synthetic": synthetic, "created_at": config.iso_now()})
    if location_id is None:
        raise Invalid("a counterparty relationship must cite a source location")
    store.get(actor, "source_locations", location_id)
    return store.insert(actor, "counterparty_links", {
        "company_id": company_id, "project_id": project_id, "counterparty_id": cp["id"],
        "relation": relation, "terms_summary": terms_summary, "location_id": location_id,
        "created_by": actor.user_id, "created_at": config.iso_now()})
