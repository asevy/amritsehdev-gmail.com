"""Tamper-evident audit chain.

Provenance (adapted): asevy/vision-edge-gateway @ 592cbff, ve_db.py
Store.audit() / verify_chain(). Changed: rows carry tenant_id; timestamps are
ISO strings from the application clock; the record holds evidence references,
software/model/prompt versions and review decisions — never document text and
never private model reasoning.
"""

from __future__ import annotations

import hashlib

from . import config
from .db import Database, dumps


def _payload(ts, tenant_id, actor, role, action, target, detail, count) -> dict:
    return {"ts": ts, "tenant_id": tenant_id, "actor": actor, "role": role,
            "action": action, "target": target, "detail": detail, "count": count}


def append(db: Database, actor, action: str, target: str = "", detail: str | dict = "",
           count: int = 0, tenant_id: str | None = None) -> str:
    if isinstance(detail, dict):
        detail = dumps(detail)
    tid = tenant_id if tenant_id is not None else getattr(actor, "tenant_id", "") or ""
    p = _payload(config.iso_now(), tid, getattr(actor, "user_id", str(actor)),
                 getattr(actor, "role", ""), action, target, detail, int(count))
    with db.lock:
        row = db.one("SELECT chain FROM audit ORDER BY seq DESC LIMIT 1")
        prev = row["chain"] if row else ""
        chain = hashlib.sha256((prev + dumps(p)).encode("utf-8")).hexdigest()
        db.execute("INSERT INTO audit(ts,tenant_id,actor,role,action,target,detail,count,chain) "
                   "VALUES(?,?,?,?,?,?,?,?,?)",
                   (p["ts"], tid, p["actor"], p["role"], action, target, detail, p["count"], chain))
    return chain


def verify_chain(db: Database) -> dict:
    prev, n = "", 0
    for r in db.all("SELECT * FROM audit ORDER BY seq ASC"):
        p = _payload(r["ts"], r["tenant_id"], r["actor"], r["role"], r["action"],
                     r["target"], r["detail"], r["count"])
        expect = hashlib.sha256((prev + dumps(p)).encode("utf-8")).hexdigest()
        if expect != r["chain"]:
            return {"ok": False, "rows": n, "broken_at_seq": r["seq"]}
        prev, n = r["chain"], n + 1
    return {"ok": True, "rows": n, "head": prev}


def tail(db: Database, tenant_id: str, limit: int = 300) -> list[dict]:
    return db.all("SELECT seq,ts,actor,role,action,target,detail,count FROM audit "
                  "WHERE tenant_id=? ORDER BY seq DESC LIMIT ?", (tenant_id, int(limit)))
