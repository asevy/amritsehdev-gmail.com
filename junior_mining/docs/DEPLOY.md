# Deployment

**Not deployed.** Nothing in this work was deployed publicly, and no
subscription, credential or external service was created. The steps below
are what a pilot deployment requires; each needs the owner's authorization.

## Single-node pilot
1. Host with an encrypted volume for `JMI_DATA_DIR` (database, per-tenant
   original documents, backups). Python ≥ 3.12; `pip install -r requirements.txt`.
2. `python -m jmi create-tenant <id> "<firm>" --seats N`;
   `python -m jmi create-user <user> admin <id>` (password prompted; 12+ chars).
3. Run `python -m jmi serve` bound to `127.0.0.1` under a process supervisor.
4. Put a TLS reverse proxy (e.g. nginx/Caddy with a real certificate) in front;
   forward `X-Forwarded-Proto: https` so the session cookie gets `Secure`.
5. Schedule `python -m jmi backup` and ship backups plus `blobs/` off-host;
   schedule `python -m jmi integrity` and alert on failure.
6. Limit request body size at the proxy to match `JMI_MAX_UPLOAD_BYTES`.

## Before real customer data
- Security review and penetration test (none performed).
- MFA/SSO (not implemented).
- Decide model-provider use; document retention/training settings of the
  selected configuration; store keys in a secret manager.
- Data-processing terms per customer; confirm licences for any market-data or
  filing connector.
- Specialist review of the metric definitions and extraction rules on real
  documents; expert-labelled benchmark run (benchmark/PROPOSAL.md).

## Scaling beyond one node
Move `Store` to PostgreSQL with row-level security keyed on `tenant_id`,
object storage with per-tenant prefixes and keys, and a job queue for
ingestion; keep the same service interfaces and tests.
