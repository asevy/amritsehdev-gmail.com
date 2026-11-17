"""Shared fixtures. Every test gets its OWN copy of a seeded SYNTHETIC
workspace (database + blobs), so tests cannot leak state into each other."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jmi import auth as AUTH, config, db as DB, facts, seed, store as STORE  # noqa: E402

PASSWORD = "correct-horse-battery-staple"
CLOCK = datetime(2026, 11, 17, 15, 0)
BASE_KEYS = ["hpg_pea", "hpg_mda", "hpg_drill", "hpg_drill_mirror", "hpg_xlsx", "hpg_deck", "market", "tvg", "obr",
             "qrc", "bwm", "broken", "other_private"]


class WS:
    def __init__(self, path: Path, ids: dict):
        self.path = path
        self.db = DB.Database(path / "jmi.sqlite3")
        self.auth = AUTH.Auth(self.db)
        self.store = STORE.Store(self.db, path)
        self.ids = ids
        self.A = seed.actor(self.store, "analyst.a")
        self.R = seed.actor(self.store, "reviewer.a")
        self.R2 = seed.actor(self.store, "reviewer2.a")
        self.V = seed.actor(self.store, "viewer.a")
        self.ADM = seed.actor(self.store, "admin.a")
        self.B = seed.actor(self.store, "analyst.b")
        self.RB = seed.actor(self.store, "reviewer.b")
        self.HPG = ids["alpha"]["HPG"]
        self.TVG = ids["alpha"]["TVG"]
        self.OBR = ids["alpha"]["OBR"]
        self.QRC = ids["alpha"]["QRC"]
        self.BWM = ids["alpha"]["BWM"]
        self.HPP = ids["projects"]["HPP"]
        self.TVP = ids["projects"]["TVP"]
        self.OBP = ids["projects"]["OBP"]
        self.HPG_B = ids["beta"]["HPG"]
        self.fixtures = path / "fx"

    def facts(self, actor=None, **where):
        return self.store.find(actor or self.A, "facts", **where)

    def fact(self, **match):
        rows = [f for f in self.facts() if all(f.get(k) == v for k, v in match.items())]
        assert rows, f"no fact matching {match}"
        return rows[0]

    def approve_all(self, actor=None):
        n = 0
        for f in self.store.find(actor or self.R, "facts"):
            if f["workflow_state"] == "source_matched":
                facts.review(self.store, actor or self.R, f["id"], "approve", "matches source (test)")
                n += 1
        return n

    def upload_key(self, key: str):
        return seed.upload_fixture(self.store, self.ids, seed.manifest_entry(self.ids, key))


@pytest.fixture(scope="session")
def base_workspace(tmp_path_factory):
    config.set_clock(CLOCK)
    path = tmp_path_factory.mktemp("base")
    d = DB.Database(path / "jmi.sqlite3")
    st = STORE.Store(d, path)
    ids = seed.seed(st, AUTH.Auth(d), path / "fx", password=PASSWORD, upload_keys=BASE_KEYS)
    d.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    d.close()
    return path, ids


@pytest.fixture
def ws(base_workspace, tmp_path):
    config.set_clock(CLOCK)
    src, ids = base_workspace
    dst = tmp_path / "ws"
    shutil.copytree(src, dst)
    for side in ("jmi.sqlite3-wal", "jmi.sqlite3-shm"):
        p = dst / side
        if p.exists():
            p.unlink()
    w = WS(dst, {**ids, "manifest": [{**m, "path": str(dst / "fx" / m["filename"])} for m in ids["manifest"]]})
    yield w
    w.db.close()
    config.set_clock(CLOCK)


@pytest.fixture
def approved(ws):
    """Workspace with every source-matched fact reviewer-approved and the NPV conflict resolved."""
    ws.approve_all()
    d = ws.store.find(ws.R, "discrepancies", kind="value_conflict")[0]
    keep = ws.fact(metric_id="npv", raw_value="412")
    facts.resolve_discrepancy(ws.store, ws.R, d["id"], "technical report is the primary disclosure", keep["id"])
    from jmi import calc
    calc.set_assumption(ws.store, ws.A, "fx_usd_cad", "1.38", "comparison assumption (test)", unit="CAD per USD",
                        as_of_date="2026-11-13", source="SYNTHETIC test entry")
    return ws


@pytest.fixture
def http(approved):
    from http_client import Client, serve_in_thread
    httpd, base = serve_in_thread(approved.store, approved.auth)

    def client(user):
        c = Client(base)
        assert c.login(user, PASSWORD), f"login failed for {user}"
        return c
    approved.client = client
    approved.base = base
    yield approved
    httpd.shutdown()
    httpd.server_close()
