"""Evidence lineage and invalidation.

Edges run source_location -> fact -> calculation -> (snapshot | memo_version |
thesis_assumption). When a fact is corrected, restated or rejected, every
current downstream output is marked stale with the reason. Approved memo
versions are flagged, never rewritten (brief §14).
"""

from __future__ import annotations

from . import config
from .auth import Actor


def link(store, actor: Actor, from_kind: str, from_id: str, to_kind: str, to_id: str) -> None:
    tenant = store.scope(actor)
    store.db.execute("INSERT OR IGNORE INTO dependencies(tenant_id,from_kind,from_id,to_kind,to_id) "
                     "VALUES(?,?,?,?,?)", (tenant, from_kind, from_id, to_kind, to_id))


def dependents(store, actor: Actor, kind: str, rid: str) -> list[tuple[str, str]]:
    tenant = store.scope(actor)
    seen, out, frontier = set(), [], [(kind, rid)]
    while frontier:
        k, i = frontier.pop()
        for r in store.db.all("SELECT to_kind, to_id FROM dependencies WHERE tenant_id=? AND from_kind=? "
                              "AND from_id=?", (tenant, k, i)):
            node = (r["to_kind"], r["to_id"])
            if node not in seen:
                seen.add(node)
                out.append(node)
                frontier.append(node)
    return out


def inputs_of(store, actor: Actor, kind: str, rid: str) -> list[tuple[str, str]]:
    tenant = store.scope(actor)
    return [(r["from_kind"], r["from_id"]) for r in store.db.all(
        "SELECT from_kind, from_id FROM dependencies WHERE tenant_id=? AND to_kind=? AND to_id=?",
        (tenant, kind, rid))]


def invalidate(store, actor: Actor, kind: str, rid: str, reason: str) -> list[dict]:
    """Mark every current output that depends on (kind, rid) as stale."""
    affected = []
    for k, i in dependents(store, actor, kind, rid):
        if k == "calculation":
            store.update(actor, "calculations", i, {"stale": 1, "stale_reason": reason})
        elif k == "snapshot":
            store.update(actor, "comparison_snapshots", i, {"stale": 1, "stale_reason": reason})
        elif k == "memo_version":
            mv = store.get(actor, "memo_versions", i)
            if mv["status"] != "superseded":
                store.update(actor, "memo_versions", i, {"stale": 1, "stale_reason": reason})
        elif k == "thesis_assumption":
            store.update(actor, "thesis_assumptions", i, {"status": "affected_by_change",
                                                           "status_reason": reason,
                                                           "updated_at": config.iso_now()})
        else:
            continue
        affected.append({"kind": k, "id": i})
    return affected
