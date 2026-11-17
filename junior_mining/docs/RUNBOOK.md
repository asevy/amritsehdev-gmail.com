# Operational runbook

## Daily
- `python -m jmi integrity` — must print `"sqlite": "ok"` and `"chain": {"ok": true}`. A broken chain means
  the audit table was altered: stop writes, preserve the file, restore from the last good backup to a separate
  path and compare.
- Review the Coverage page: any `ingestion failed` or `stale` company is visible to users already; assign
  follow-up.
- `python -m jmi worker` retries failed/queued ingestion runs. A permanently unreadable file stays failed
  and visible; replace it with a readable version via upload (new version).

## Backups and restore
- `python -m jmi backup /secure/backups` — consistent online snapshot (writes continue).
- Copy backups off the host (not automated in this build) and keep the per-tenant `blobs/` directory with
  them; facts reference blobs by hash.
- Restore: stop the server; `jmi.db.Database.restore(backup, live_path)` refuses a backup that fails
  `integrity_check`; restart; run `integrity`.
- Recovery point = last backup.

## Incident handling
| Incident | Action |
|---|---|
| Wrong value approved | Correct it (`/fact/<id>` → new revision). Dependents become stale automatically and an event lists them. A different reviewer approves the revision. Approved memos show "changed since approval"; issue a new memo version. |
| Extraction rule defect | Fix the rule; bump `EXTRACTOR_VERSION`; rerun tests and the benchmark; re-ingest affected documents (new runs have a new idempotency key). Existing facts keep their extractor version for traceability. |
| Suspected cross-tenant exposure | Disable affected users (`Auth.set_active`), export the audit tail for both tenants, check `document_viewed` / `export` / `search` rows; tests in `test_14` define expected behaviour. |
| Policy guard blocked a response (HTTP 500 `policy_guard`) | A score-like field reached an API payload — treat as a release-blocking defect; find via server log. |
| Feed failure | Visible on Coverage and in the inbox; nothing is shown as current while failed. |

## Change control and regression
Rerun `python -m pytest` and `python -m jmi.bench` after any change to models,
prompts, parsers, extraction rules, schema, calculations or retrieval.
Schema changes are new numbered migrations; never edit an applied migration.
Definition changes add a version to the metric (facts keep the version they
were produced under). Rollback: redeploy the previous commit; migrations are
additive, so a rollback with a newer schema requires restoring the pre-change
backup.

## Data handling
Never upload real private deal documents or real issuer analysis into a
development workspace. Synthetic fixtures are labelled. No external messages
are sent by the application; notifications are in-app only.
