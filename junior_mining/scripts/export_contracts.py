"""Generate data/API contracts from the code itself, so documentation cannot
drift from implementation:

    python scripts/export_contracts.py      # writes docs/contracts/*.json
"""

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jmi import calc, definitions  # noqa: E402
from jmi.db import migrate  # noqa: E402
from jmi.server import ACTIONS, GET_ROUTES  # noqa: E402
from jmi.store import JSON_COLUMNS, MUTABLE, TENANT_TABLES  # noqa: E402

out = ROOT / "docs" / "contracts"
out.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(":memory:")
migrate(conn)
schema = {}
for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                         "AND name NOT LIKE 'passages_fts_%' ORDER BY name"):
    cols = [{"name": r[1], "type": r[2], "not_null": bool(r[3]), "default": r[4], "primary_key": bool(r[5]),
             "json": r[1] in JSON_COLUMNS.get(t, set()), "mutable_after_insert": r[1] in MUTABLE.get(t, set())}
            for r in conn.execute(f"PRAGMA table_info({t})")]
    schema[t] = {"tenant_scoped": t in TENANT_TABLES, "columns": cols}
(out / "schema.json").write_text(json.dumps(schema, indent=1))
api = {"auth": "Session cookie 'jmisess' (HttpOnly, SameSite=Strict) from POST /login; every POST also needs the "
               "session CSRF token: header X-JMI-CSRF (JSON) or form field csrf.",
       "errors": {"400": "invalid input / bad_csrf", "401": "not signed in", "403": "role lacks capability",
                  "404": "not found — including any record belonging to another tenant", "413": "too large",
                  "500": "server error or policy_guard (score-like field blocked)"},
       "get_routes": [{"pattern": p, "handler": h} for p, h in GET_ROUTES],
       "post_actions": sorted(f"/api/{k}" for k in ACTIONS)}
(out / "api.json").write_text(json.dumps(api, indent=1))
(out / "definitions.json").write_text(json.dumps({"metrics": definitions.registry(),
                                                  "calculations": calc.definitions()}, indent=1, default=str))
print("wrote", ", ".join(p.name for p in sorted(out.glob("*.json"))))
