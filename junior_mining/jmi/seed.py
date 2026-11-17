"""Seed a SYNTHETIC workspace for development, tests and the demonstration.

Two tenants are created so isolation can be exercised:
  alpha — "Synthetic Resource Fund A" (all fixture companies)
  beta  — "Other Fund LP (synthetic)" (its own record of one company and a private file)

Passwords are generated per run unless supplied; nothing here is a real
credential, and the seeding refuses to run against a database that already
has tenants unless asked to extend it.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from . import entities, ingest, monitoring
from .auth import Actor, Auth, CAPS
from .store import Store

USERS = {
    "alpha": [("admin.a", "admin"), ("analyst.a", "analyst"), ("reviewer.a", "reviewer"),
              ("reviewer2.a", "reviewer"), ("viewer.a", "read_only")],
    "beta": [("analyst.b", "analyst"), ("reviewer.b", "reviewer")],
}


def actor(store: Store, user_id: str) -> Actor:
    u = store.db.one("SELECT * FROM users WHERE user_id=?", (user_id,))
    return Actor(u["user_id"], u["role"], u["tenant_id"], CAPS[u["role"]])


def seed(store: Store, auth: Auth, fixture_dir: Path, *, password: str | None = None,
         upload_keys: list[str] | None = None) -> dict:
    import sys
    from . import config
    if str(config.PROJECT_DIR) not in sys.path:
        sys.path.insert(0, str(config.PROJECT_DIR))
    from fixtures import synthetic
    if store.db.one("SELECT COUNT(*) n FROM tenants")["n"]:
        raise RuntimeError("database already has tenants; seed only an empty database")
    password = password or secrets.token_urlsafe(12)
    auth.create_tenant("alpha", "Synthetic Resource Fund A", plan="pilot", seats=10,
                       entitlements={"companies": 50, "documents_per_month": 500})
    auth.create_tenant("beta", "Other Fund LP (synthetic)", plan="pilot", seats=5,
                       entitlements={"companies": 10})
    for tenant, users in USERS.items():
        for uid, role in users:
            auth.create_user(uid, password, role, tenant)
    manifest = synthetic.build(fixture_dir)
    ids = {"alpha": {}, "beta": {}, "projects": {}, "password": password, "manifest": manifest}

    a = actor(store, "analyst.a")
    monitoring.seed_feeds(store, a)
    for key, spec in synthetic.COMPANIES.items():
        c = entities.create_company(store, a, spec["name"], reporting_currency=spec["currency"], synthetic=True)
        ids["alpha"][key] = c["id"]
        entities.add_listing(store, a, c["id"], "XSYN", spec["ticker"], spec["listing_currency"])
        for p in spec["projects"]:
            pr = entities.create_project(store, a, c["id"], p["name"], commodity=p["commodity"],
                                         jurisdiction=p["jurisdiction"], country=p["country"], stage=p["stage"],
                                         deposit_type=p["deposit_type"], process_route=p["process_route"],
                                         interest_pct=p["interest_pct"], interest_kind=p["interest_kind"],
                                         effective_date=p["effective_date"], aliases=p["aliases"], synthetic=True)
            ids["projects"][p["key"]] = pr["id"]
    b = actor(store, "analyst.b")
    monitoring.seed_feeds(store, b)
    cb = entities.create_company(store, b, "Halvard Peak Gold Corp.", reporting_currency="CAD", synthetic=True)
    ids["beta"]["HPG"] = cb["id"]

    for m in manifest:
        if upload_keys is not None and m["key"] not in upload_keys:
            continue
        upload_fixture(store, ids, m)
    return ids


def upload_fixture(store: Store, ids: dict, m: dict) -> dict:
    who = actor(store, "analyst.a" if m["tenant"] == "alpha" else "analyst.b")
    company = ids[m["tenant"]].get(m["company"]) if m["company"] else None
    return ingest.upload(store, who, filename=m["filename"], data=Path(m["path"]).read_bytes(), title=m["title"],
                         doc_type=m["doc_type"], company_id=company, publisher=m["publisher"],
                         publication_date=m["publication_date"], reporting_currency=m["reporting_currency"],
                         is_issuer_primary=m["is_issuer_primary"], synthetic=True)


def manifest_entry(ids: dict, key: str) -> dict:
    return next(m for m in ids["manifest"] if m["key"] == key)
