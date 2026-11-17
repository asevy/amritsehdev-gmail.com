"""One event system. News, milestones, commitment changes, restatements,
ingestion failures and thesis changes are all events with links, so the
timeline, change inbox and thesis-change views read the same records and
cannot disagree. Notifications are in-app only: no email or external channel
exists in this build (brief §12).
"""

from __future__ import annotations

from . import config
from .auth import Actor


def emit(store, actor: Actor, kind: str, title: str, *, company_id: str | None = None,
         project_id: str | None = None, detail: dict | None = None, source_version_id: str | None = None,
         event_date: str | None = None, dedupe_key: str | None = None,
         links: list[tuple[str, str]] | None = None, duplicate_of: str | None = None,
         notify: bool = True) -> dict:
    tenant = store.scope(actor)
    if dedupe_key:
        prior = store.db.one("SELECT * FROM events WHERE tenant_id=? AND dedupe_key=? AND duplicate_of IS NULL",
                             (tenant, dedupe_key))
        if prior and not duplicate_of:
            return store.decode("events", prior)
    ev = store.insert(actor, "events", {
        "company_id": company_id, "project_id": project_id, "kind": kind, "title": title,
        "detail": detail or {}, "source_version_id": source_version_id,
        "event_date": event_date or config.today().isoformat(), "dedupe_key": dedupe_key,
        "duplicate_of": duplicate_of,
        "status": "dismissed" if duplicate_of else "new",
        "status_reason": "duplicate of an earlier event (mirrored disclosure)" if duplicate_of else "",
        "created_at": config.iso_now()})
    for k, i in links or []:
        store.db.execute("INSERT OR IGNORE INTO event_links(tenant_id,event_id,kind,target_id) VALUES(?,?,?,?)",
                         (tenant, ev["id"], k, i))
    if notify and not duplicate_of:
        store.insert(actor, "notifications", {"user_id": None, "event_id": ev["id"], "message": title,
                                              "created_at": config.iso_now()})
    return ev


def links_of(store, actor: Actor, event_id: str) -> list[dict]:
    tenant = store.scope(actor)
    return store.db.all("SELECT kind, target_id FROM event_links WHERE tenant_id=? AND event_id=?",
                        (tenant, event_id))


def set_status(store, actor: Actor, event_id: str, status: str, reason: str) -> None:
    if status not in ("reviewed", "dismissed", "resolved"):
        raise ValueError("status must be reviewed, dismissed or resolved")
    if status == "dismissed" and not reason.strip():
        raise ValueError("a dismissal requires a reason")
    store.require(actor, "write")
    store.update(actor, "events", event_id, {"status": status, "status_reason": reason,
                                             "reviewed_by": actor.user_id, "reviewed_at": config.iso_now()})
    store.audit(actor, f"event_{status}", event_id, reason[:200])
