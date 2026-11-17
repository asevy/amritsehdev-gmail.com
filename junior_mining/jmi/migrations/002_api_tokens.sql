-- 002_api_tokens.sql — personal access tokens for the Claude (MCP) connector.
-- Tokens are stored as SHA-256 digests; the token itself is shown once at
-- creation. A token acts as its user (same role, same tenant), read-only.
CREATE TABLE api_tokens (
    id           TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    user_id      TEXT NOT NULL REFERENCES users(user_id),
    token_sha    TEXT NOT NULL UNIQUE,
    label        TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    last_used_at TEXT,
    revoked_at   TEXT
);
CREATE INDEX api_tokens_user ON api_tokens(tenant_id, user_id);
