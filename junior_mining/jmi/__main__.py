"""Command line.

    python -m jmi serve                     # http://127.0.0.1:8780
    python -m jmi seed-demo                 # SYNTHETIC workspace; prints generated passwords once
    python -m jmi create-tenant ID NAME     # a real (empty) tenant
    python -m jmi create-user USER ROLE TENANT
    python -m jmi worker                    # retry failed ingestion runs (all tenants)
    python -m jmi integrity                 # SQLite integrity + audit chain
    python -m jmi backup DEST_DIR
    python -m jmi definitions               # metric and formula registry (JSON)

Data directory: $JMI_DATA_DIR (default ./data). Nothing here contacts a third
party, sends messages or collects payment.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from . import config, ingest
from .auth import Auth, ROLES
from .db import Database
from .store import Store


def _open(settings):
    db = Database(settings.data_dir / "jmi.sqlite3")
    return db, Auth(db, settings.session_ttl_seconds), Store(db, settings.data_dir, settings)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jmi")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--host")
    s.add_argument("--port", type=int)
    sub.add_parser("seed-demo")
    t = sub.add_parser("create-tenant")
    t.add_argument("tenant_id")
    t.add_argument("name")
    t.add_argument("--seats", type=int, default=5)
    u = sub.add_parser("create-user")
    u.add_argument("user_id")
    u.add_argument("role", choices=ROLES)
    u.add_argument("tenant_id")
    sub.add_parser("worker")
    tk = sub.add_parser("create-api-token", help="read-only token for the Claude (MCP) connector; shown once")
    tk.add_argument("user_id")
    tk.add_argument("--label", default="Claude connector")
    sub.add_parser("mcp", help="run the Claude connector over stdio (needs JMI_API_TOKEN)")
    cs = sub.add_parser("claude-settings", help="show or set a tenant's Claude API settings")
    cs.add_argument("tenant_id")
    cs.add_argument("--enable", action="store_true")
    cs.add_argument("--disable", action="store_true")
    cs.add_argument("--api-key-env", help="NAME of the environment variable holding the firm's Anthropic API key")
    cs.add_argument("--model")
    cs.add_argument("--auto-extract", action="store_true")
    sub.add_parser("integrity")
    b = sub.add_parser("backup")
    b.add_argument("dest")
    sub.add_parser("definitions")
    args = ap.parse_args(argv)
    settings = config.load_settings()

    if args.cmd == "definitions":
        from . import calc, definitions
        print(json.dumps({"metrics": definitions.registry(), "calculations": calc.definitions()}, indent=1, default=str))
        return 0
    db, auth, store = _open(settings)
    if args.cmd == "serve":
        from .server import make_server
        host, port = args.host or settings.host, args.port or settings.port
        chain = db.integrity()
        if not chain["chain"]["ok"]:
            print(f"  ! AUDIT CHAIN BROKEN at seq {chain['chain'].get('broken_at_seq')}")
        httpd = make_server(store, auth, host, port)
        print(f"Junior Mining Intelligence on http://{host}:{port}/login  (data: {settings.data_dir})")
        if host not in ("127.0.0.1", "localhost"):
            print("  ! bound beyond localhost over plain HTTP — put a TLS proxy in front before real data")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("stopped")
        return 0
    if args.cmd == "seed-demo":
        from . import seed
        ids = seed.seed(store, auth, settings.data_dir / "fixtures", upload_keys=[
            m for m in ("hpg_pea", "hpg_mda", "hpg_drill", "hpg_drill_mirror", "hpg_xlsx", "hpg_deck", "market", "tvg",
                        "obr", "qrc", "bwm", "broken", "other_private")])
        print("SYNTHETIC workspace created. Generated password for every seeded user (shown once):")
        print("  ", ids["password"])
        for tenant, users in seed.USERS.items():
            for uid, role in users:
                print(f"   {uid:<14} {role:<10} tenant={tenant}")
        print("The update release (fixtures/HPG_NR_2026-11-16_resource_update.pdf) is NOT uploaded; upload it "
              "to demonstrate change detection.")
        return 0
    if args.cmd == "create-tenant":
        from . import monitoring
        from .auth import system_actor
        auth.create_tenant(args.tenant_id, args.name, seats=args.seats)
        monitoring.seed_feeds(store, system_actor(args.tenant_id, "setup"))
        print(f"tenant {args.tenant_id} created; connector inventory recorded as not configured")
        return 0
    if args.cmd == "create-user":
        pw = getpass.getpass("Password (12+ characters): ")
        auth.create_user(args.user_id, pw, args.role, args.tenant_id)
        print("user created")
        return 0
    if args.cmd == "worker":
        n = 0
        for r in db.all("SELECT id, tenant_id FROM ingestion_runs WHERE status IN ('failed','queued')"):
            res = ingest.process(store, r["tenant_id"], r["id"])
            print(r["id"], res["status"], res["error"][:100])
            n += 1
        print(f"{n} run(s) processed")
        return 0
    if args.cmd == "create-api-token":
        token = auth.create_api_token(args.user_id, args.label)
        print("Connector token (shown once; store it in Claude's connector config, not in git):")
        print(token)
        return 0
    if args.cmd == "mcp":
        db.close()
        from . import mcp_server
        return mcp_server.main()
    if args.cmd == "claude-settings":
        from . import claude
        from .auth import Actor, CAPS
        admin = Actor("cli-admin", "admin", args.tenant_id, CAPS["admin"])
        if args.enable or args.disable:
            claude.set_config(store, admin, enabled=args.enable and not args.disable, api_key_env=args.api_key_env,
                              model=args.model, auto_extract=args.auto_extract)
        print(json.dumps({**claude.get_config(store, admin),
                          "credential": claude.credential_status(store, admin)}, indent=1))
        return 0
    if args.cmd == "integrity":
        print(json.dumps(db.integrity(), indent=1))
        return 0
    if args.cmd == "backup":
        print(db.backup(args.dest))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
