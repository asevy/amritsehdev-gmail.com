"""SQLite connection, migrations, transactions, backup and restore.

Provenance (adapted, not imported):
  * migrate()  — asevy/mso-ip-lab @ a1b3fd4, src/mso_ip_lab/storage/db.py
                 (numbered SQL files, schema_migrations tracking). Changed:
                 each migration and its marker now commit atomically.
  * Database._tx / backup / restore — asevy/vision-edge-gateway @ 592cbff,
                 ve_db.py Store._tx, backup(), restore(). Changed: nested
                 transactions via a depth counter; a process-wide RLock
                 serialises access from the threaded HTTP server.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply unapplied migrations in lexical order. Returns the ids applied.

    A migration and its schema_migrations marker are committed together, so a
    failure leaves neither behind and a re-run retries cleanly.
    """
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                 "id INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    applied = {int(r[0]) for r in conn.execute("SELECT id FROM schema_migrations")}
    done: list[int] = []
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        try:
            mig_id = int(sql_file.stem.split("_", 1)[0])
        except ValueError as exc:
            raise RuntimeError(f"migration '{sql_file.name}' must start with an integer") from exc
        if mig_id in applied:
            continue
        script = sql_file.read_text(encoding="utf-8")
        try:
            conn.executescript("BEGIN;\n" + script +
                               f"\nINSERT INTO schema_migrations(id) VALUES ({mig_id});\nCOMMIT;")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        done.append(mig_id)
    return done


def dumps(obj: Any) -> str:
    """Canonical JSON: stable key order, so hashes and comparisons are stable."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


class Database:
    def __init__(self, path: str | Path):
        self.path = path
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        if str(path) != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=FULL")
        self.lock = threading.RLock()
        self._depth = 0
        with self.lock:
            migrate(self.conn)
        if str(path) != ":memory:":
            try:
                Path(path).chmod(0o600)
            except OSError:
                pass

    # ------------------------------------------------------------ access
    @contextmanager
    def tx(self) -> Iterator[None]:
        with self.lock:
            outer = self._depth == 0
            if outer:
                self.conn.execute("BEGIN IMMEDIATE")
            self._depth += 1
            try:
                yield
            except BaseException:
                self._depth -= 1
                if outer:
                    self.conn.execute("ROLLBACK")
                raise
            else:
                self._depth -= 1
                if outer:
                    self.conn.execute("COMMIT")

    def execute(self, sql: str, params: tuple | list = ()) -> sqlite3.Cursor:
        with self.lock:
            return self.conn.execute(sql, params)

    def all(self, sql: str, params: tuple | list = ()) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | list = ()) -> dict | None:
        with self.lock:
            r = self.conn.execute(sql, params).fetchone()
            return dict(r) if r else None

    def columns(self, table: str) -> list[str]:
        with self.lock:
            return [r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")]

    # ------------------------------------------------------------ durability
    def backup(self, dest_dir: Path) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / ("jmi-%s.sqlite3" % time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
        target = sqlite3.connect(str(dest))
        try:
            with self.lock, target:
                self.conn.backup(target)
        finally:
            target.close()
        try:
            dest.chmod(0o600)
        except OSError:
            pass
        return dest

    def integrity(self) -> dict:
        from . import audit
        row = self.one("PRAGMA integrity_check")
        return {"sqlite": list(row.values())[0] if row else "unknown",
                "chain": audit.verify_chain(self)}

    @staticmethod
    def restore(backup_file: Path, live_path: Path) -> dict:
        """Verify a backup, then put it in place. Never swaps in an unreadable file."""
        backup_file, live_path = Path(backup_file), Path(live_path)
        probe = sqlite3.connect(str(backup_file))
        try:
            if probe.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("backup fails integrity_check; refusing to restore")
        finally:
            probe.close()
        if live_path.exists():
            live_path.replace(live_path.with_suffix(".sqlite3.replaced"))
        for side in ("-wal", "-shm"):
            stale = Path(str(live_path) + side)
            if stale.exists():
                stale.unlink()
        live_path.write_bytes(backup_file.read_bytes())
        return {"restored": str(live_path)}

    def close(self) -> None:
        with self.lock:
            self.conn.close()
