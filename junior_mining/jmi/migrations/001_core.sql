-- 001_core.sql — canonical records for Junior Mining Intelligence.
--
-- Conventions
--   * Every tenant-owned row carries tenant_id. No query in the application
--     reads a tenant-owned table without a tenant predicate (jmi/store.py).
--   * Decimal quantities are stored as TEXT and parsed with decimal.Decimal.
--     NULL means "not established"; a stated zero is stored as '0'.
--   * JSON columns hold arrays/objects serialised with sorted keys.
--   * Evidence rows are append-only in value: a correction is a new row that
--     points at the row it revises (revision_of). Workflow state is the only
--     mutable column on facts.

CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);

-- ------------------------------------------------------------ tenancy & access
CREATE TABLE tenants (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    plan          TEXT NOT NULL DEFAULT 'pilot',
    seats         INTEGER NOT NULL DEFAULT 5,
    entitlements  TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL
);

CREATE TABLE users (
    user_id       TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL REFERENCES tenants(id),
    role          TEXT NOT NULL,
    salt          TEXT NOT NULL,
    hash          TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL,
    password_changed_at TEXT
);

-- Session tokens are stored hashed: a copy of the database does not yield
-- usable sessions.
CREATE TABLE sessions (
    token_sha     TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(user_id),
    csrf          TEXT NOT NULL,
    expires       REAL NOT NULL
);

CREATE TABLE workspaces (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
    created_by TEXT NOT NULL, created_at TEXT NOT NULL
);

-- ------------------------------------------------------------ entities
CREATE TABLE companies (
    id                 TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    name               TEXT NOT NULL,
    legal_name         TEXT,
    incorporation      TEXT,
    reporting_currency TEXT,
    fiscal_year_end    TEXT,
    synthetic          INTEGER NOT NULL DEFAULT 0,
    created_by         TEXT NOT NULL,
    created_at         TEXT NOT NULL
);
CREATE INDEX companies_tenant ON companies(tenant_id);

CREATE TABLE projects (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    name             TEXT NOT NULL,
    commodity        TEXT,
    jurisdiction     TEXT,
    country          TEXT,
    stage            TEXT,
    stage_source_location_id TEXT,
    deposit_type     TEXT,
    process_route    TEXT,
    infrastructure   TEXT NOT NULL DEFAULT '[]',
    synthetic        INTEGER NOT NULL DEFAULT 0,
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX projects_tenant ON projects(tenant_id);

-- Former names, tickers, subsidiaries and project aliases, with validity.
CREATE TABLE entity_aliases (
    id           TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    entity_kind  TEXT NOT NULL,          -- company | project
    entity_id    TEXT NOT NULL,
    alias        TEXT NOT NULL,
    alias_kind   TEXT NOT NULL,          -- name | former_name | subsidiary | project_alias | abbreviation
    valid_from   TEXT,
    valid_to     TEXT,
    created_by   TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE INDEX aliases_tenant ON entity_aliases(tenant_id, entity_kind);

CREATE TABLE listings (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    company_id  TEXT NOT NULL REFERENCES companies(id),
    exchange    TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    currency    TEXT,
    valid_from  TEXT,
    valid_to    TEXT,
    created_at  TEXT NOT NULL
);

-- Historical ownership is preserved: a change closes the old row (end_date)
-- and opens a new one. Never updated in place otherwise.
CREATE TABLE ownership_interests (
    id             TEXT PRIMARY KEY,
    tenant_id      TEXT NOT NULL,
    company_id     TEXT NOT NULL REFERENCES companies(id),
    project_id     TEXT NOT NULL REFERENCES projects(id),
    interest_pct   TEXT,                 -- decimal percent, NULL = not established
    interest_kind  TEXT NOT NULL DEFAULT 'direct',  -- direct | joint_venture | earn_in | option
    effective_date TEXT,
    end_date       TEXT,
    fact_id        TEXT,
    notes          TEXT NOT NULL DEFAULT '',
    created_by     TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE counterparties (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT '', synthetic INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE counterparty_links (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    company_id      TEXT NOT NULL,
    project_id      TEXT,
    counterparty_id TEXT NOT NULL REFERENCES counterparties(id),
    relation        TEXT NOT NULL,       -- royalty | stream | offtake | lender | jv_partner | contractor | option_counterparty
    terms_summary   TEXT NOT NULL DEFAULT '',
    location_id     TEXT,
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

-- ------------------------------------------------------------ documents
CREATE TABLE documents (
    id                TEXT PRIMARY KEY,
    tenant_id         TEXT NOT NULL,
    company_id        TEXT,               -- NULL for multi-issuer files (e.g. market snapshots)
    title             TEXT NOT NULL,
    doc_type          TEXT NOT NULL,      -- technical_report | mda | financial_statements | news_release | presentation | market_data | other
    publisher         TEXT NOT NULL DEFAULT '',
    is_issuer_primary INTEGER NOT NULL DEFAULT 0,
    created_by        TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE TABLE document_versions (
    id                    TEXT PRIMARY KEY,
    tenant_id             TEXT NOT NULL,
    document_id           TEXT NOT NULL REFERENCES documents(id),
    version_no            INTEGER NOT NULL,
    sha256                TEXT NOT NULL,
    text_fingerprint      TEXT,
    size_bytes            INTEGER NOT NULL,
    filename              TEXT NOT NULL,
    mime                  TEXT NOT NULL,
    storage_path          TEXT NOT NULL,
    publication_date      TEXT,
    retrieved_at          TEXT NOT NULL,
    source_url            TEXT NOT NULL DEFAULT '',
    reporting_currency    TEXT,
    supersedes_version_id TEXT,
    mirror_of_version_id  TEXT,
    mirror_similarity     TEXT,
    page_count            INTEGER,
    unreadable_pages      TEXT NOT NULL DEFAULT '[]',
    parse_status          TEXT NOT NULL DEFAULT 'pending',   -- pending | parsed | partial | failed
    parse_warnings        TEXT NOT NULL DEFAULT '[]',
    synthetic             INTEGER NOT NULL DEFAULT 0,
    uploaded_by           TEXT NOT NULL,
    uploaded_at           TEXT NOT NULL,
    UNIQUE (tenant_id, sha256)
);

CREATE TABLE pages (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    version_id  TEXT NOT NULL REFERENCES document_versions(id),
    page_no     INTEGER NOT NULL,
    label       TEXT NOT NULL DEFAULT '',   -- e.g. sheet name for spreadsheets
    text        TEXT NOT NULL,
    readable    INTEGER NOT NULL,
    UNIQUE (version_id, page_no)
);

CREATE TABLE doc_tables (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    version_id  TEXT NOT NULL,
    page_no     INTEGER NOT NULL,
    table_index INTEGER NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    rows        TEXT NOT NULL,            -- JSON [[cell,...],...] exactly as extracted
    footnotes   TEXT NOT NULL DEFAULT '[]'
);

-- An exact place in an exact document version. Coordinates (bbox) are stored
-- only when the PDF text layer supplied them; they are never estimated.
CREATE TABLE source_locations (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    version_id  TEXT NOT NULL REFERENCES document_versions(id),
    page_no     INTEGER NOT NULL,
    table_index INTEGER,
    row_index   INTEGER,
    col_index   INTEGER,
    cell_ref    TEXT,
    char_start  INTEGER,
    char_end    INTEGER,
    quote       TEXT NOT NULL,
    context     TEXT NOT NULL DEFAULT '',
    row_header  TEXT,
    col_header  TEXT,
    footnotes   TEXT NOT NULL DEFAULT '[]',
    bbox        TEXT,
    bbox_note   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX locations_version ON source_locations(version_id);

-- Derived, rebuildable retrieval index. tenant_id is filtered on every query.
CREATE VIRTUAL TABLE passages_fts USING fts5(
    text, tenant_id UNINDEXED, version_id UNINDEXED, page_no UNINDEXED,
    company_id UNINDEXED, tokenize = 'porter unicode61'
);

CREATE TABLE ingestion_runs (
    id                TEXT PRIMARY KEY,
    tenant_id         TEXT NOT NULL,
    version_id        TEXT NOT NULL,
    idempotency_key   TEXT NOT NULL UNIQUE,
    status            TEXT NOT NULL,       -- queued | running | succeeded | failed
    attempts          INTEGER NOT NULL DEFAULT 0,
    error             TEXT NOT NULL DEFAULT '',
    parser            TEXT NOT NULL DEFAULT '',
    parser_version    TEXT NOT NULL DEFAULT '',
    extractor         TEXT NOT NULL DEFAULT '',
    extractor_version TEXT NOT NULL DEFAULT '',
    candidates        INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL,
    started_at        TEXT,
    finished_at       TEXT
);

-- ------------------------------------------------------------ facts
CREATE TABLE facts (
    id                 TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    company_id         TEXT NOT NULL,
    project_id         TEXT,
    metric_id          TEXT NOT NULL,
    definition_version INTEGER NOT NULL,
    raw_text           TEXT NOT NULL,     -- exact source quote
    raw_value          TEXT,              -- the token as printed
    normalized_value   TEXT,              -- canonical Decimal text / enum token; NULL = unknown
    value_kind         TEXT NOT NULL,     -- decimal | enum | text
    unit               TEXT,
    currency           TEXT,
    precision_lo       TEXT,
    precision_hi       TEXT,
    transformations    TEXT NOT NULL DEFAULT '[]',
    scope_basis        TEXT,              -- 100% | attributable
    period_start       TEXT,
    period_end         TEXT,
    as_of_date         TEXT,
    effective_date     TEXT,
    publication_date   TEXT,
    retrieved_at       TEXT,
    study_type         TEXT,
    tax_basis          TEXT,
    discount_rate      TEXT,
    resource_category  TEXT,
    reporting_basis    TEXT,              -- inclusive | exclusive (of reserves)
    estimate_status    TEXT,              -- current | historical
    qualifiers         TEXT NOT NULL DEFAULT '{}',
    attribution        TEXT NOT NULL,
    evidence_type      TEXT NOT NULL,     -- observed | reported | calculated | forecast | unknown_disputed
    workflow_state     TEXT NOT NULL,
    checks             TEXT NOT NULL DEFAULT '[]',
    missing_reason     TEXT,
    version_id         TEXT,
    location_id        TEXT,
    equivalence_key    TEXT NOT NULL,
    revision_of        TEXT,
    relation           TEXT,              -- correction | restatement | scope_change
    extractor          TEXT NOT NULL DEFAULT '',
    extractor_version  TEXT NOT NULL DEFAULT '',
    ingestion_run_id   TEXT,
    created_by         TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
CREATE INDEX facts_company ON facts(tenant_id, company_id, metric_id);
CREATE INDEX facts_key ON facts(tenant_id, equivalence_key);
CREATE INDEX facts_state ON facts(tenant_id, workflow_state);

CREATE TABLE review_decisions (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    target_kind TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    decision    TEXT NOT NULL,
    from_state  TEXT,
    to_state    TEXT,
    reason      TEXT NOT NULL DEFAULT '',
    actor       TEXT NOT NULL,
    at          TEXT NOT NULL
);
CREATE INDEX reviews_target ON review_decisions(tenant_id, target_kind, target_id);

CREATE TABLE discrepancies (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    company_id  TEXT NOT NULL,
    kind        TEXT NOT NULL,     -- value_conflict | restatement | definition_mismatch | entity_ambiguity | category_mismatch
    fact_a      TEXT NOT NULL,
    fact_b      TEXT,
    detail      TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'open',   -- open | resolved
    resolution  TEXT NOT NULL DEFAULT '',
    resolved_by TEXT,
    resolved_at TEXT,
    created_at  TEXT NOT NULL
);

-- ------------------------------------------------------------ calculations
CREATE TABLE assumptions (
    id                 TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    company_id         TEXT,
    name               TEXT NOT NULL,     -- e.g. fx_usd_cad, monthly_spend, participation_rate
    value              TEXT NOT NULL,
    unit               TEXT NOT NULL DEFAULT '',
    as_of_date         TEXT,
    source             TEXT NOT NULL DEFAULT '',
    rationale          TEXT NOT NULL,
    created_by         TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    superseded_by      TEXT
);

CREATE TABLE calculations (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    company_id      TEXT,
    formula_id      TEXT NOT NULL,
    formula_version INTEGER NOT NULL,
    label           TEXT NOT NULL,
    status          TEXT NOT NULL,     -- computed | withheld
    output_value    TEXT,
    output_unit     TEXT,
    display_value   TEXT,
    inputs          TEXT NOT NULL DEFAULT '[]',
    missing         TEXT NOT NULL DEFAULT '[]',
    warnings        TEXT NOT NULL DEFAULT '[]',
    caveats         TEXT NOT NULL DEFAULT '[]',
    parameters      TEXT NOT NULL DEFAULT '{}',
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    stale           INTEGER NOT NULL DEFAULT 0,
    stale_reason    TEXT NOT NULL DEFAULT ''
);

-- Many-to-many lineage: source -> fact -> calculation -> claim/memo/snapshot.
CREATE TABLE dependencies (
    tenant_id TEXT NOT NULL,
    from_kind TEXT NOT NULL, from_id TEXT NOT NULL,
    to_kind   TEXT NOT NULL, to_id   TEXT NOT NULL,
    PRIMARY KEY (tenant_id, from_kind, from_id, to_kind, to_id)
);
CREATE INDEX deps_from ON dependencies(tenant_id, from_kind, from_id);

-- ------------------------------------------------------------ risks & diligence
CREATE TABLE risk_findings (
    id                   TEXT PRIMARY KEY,
    tenant_id            TEXT NOT NULL,
    company_id           TEXT NOT NULL,
    project_id           TEXT,
    category             TEXT NOT NULL,
    title                TEXT NOT NULL,
    consequence          TEXT NOT NULL DEFAULT '',
    dependencies_text    TEXT NOT NULL DEFAULT '',
    mitigants            TEXT NOT NULL DEFAULT '',
    unresolved_questions TEXT NOT NULL DEFAULT '',
    monitoring_trigger   TEXT NOT NULL DEFAULT '',
    owner                TEXT NOT NULL DEFAULT '',
    reviewer             TEXT NOT NULL DEFAULT '',
    status               TEXT NOT NULL,   -- open_question | documented_finding | mitigated | resolved | dismissed
    attention            INTEGER NOT NULL DEFAULT 0,
    attention_reason     TEXT NOT NULL DEFAULT '',
    origin               TEXT NOT NULL,   -- analyst | rule:<id>
    created_by           TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE risk_evidence (
    id            TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL,
    risk_id       TEXT NOT NULL REFERENCES risk_findings(id),
    stance        TEXT NOT NULL,       -- supporting | contrary
    fact_id       TEXT,
    location_id   TEXT,
    note          TEXT NOT NULL DEFAULT '',
    evidence_date TEXT,
    added_by      TEXT NOT NULL,
    added_at      TEXT NOT NULL
);

CREATE TABLE risk_history (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, risk_id TEXT NOT NULL,
    actor TEXT NOT NULL, at TEXT NOT NULL, change TEXT NOT NULL
);

CREATE TABLE diligence_items (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    company_id       TEXT NOT NULL,
    project_id       TEXT,
    template         TEXT NOT NULL,
    item_key         TEXT NOT NULL,
    title            TEXT NOT NULL,
    specialist       TEXT NOT NULL DEFAULT '',
    required_metrics TEXT NOT NULL DEFAULT '[]',
    status           TEXT NOT NULL DEFAULT 'open',  -- open | evidence_attached | reviewed | not_applicable
    evidence         TEXT NOT NULL DEFAULT '[]',
    notes            TEXT NOT NULL DEFAULT '',
    reviewed_by      TEXT,
    reviewed_at      TEXT,
    UNIQUE (tenant_id, company_id, project_id, item_key)
);

CREATE TABLE diligence_questions (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    company_id       TEXT NOT NULL,
    project_id       TEXT,
    item_id          TEXT,
    question         TEXT NOT NULL,
    specialist       TEXT NOT NULL DEFAULT '',
    document_request TEXT NOT NULL DEFAULT '',
    status           TEXT NOT NULL DEFAULT 'open',   -- open | answered | closed
    answer_fact_id   TEXT,
    origin           TEXT NOT NULL,
    dedupe_key       TEXT,
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    UNIQUE (tenant_id, dedupe_key)
);

CREATE TABLE commitments (
    id                  TEXT PRIMARY KEY,
    tenant_id           TEXT NOT NULL,
    company_id          TEXT NOT NULL,
    project_id          TEXT,
    original_wording    TEXT NOT NULL,
    attribution         TEXT NOT NULL,
    stated_on           TEXT,
    location_id         TEXT NOT NULL,
    subject             TEXT NOT NULL,
    target_text         TEXT NOT NULL,
    target_window_start TEXT,
    target_window_end   TEXT,
    window_note         TEXT NOT NULL DEFAULT '',
    conditions          TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'pending', -- pending | met | revised | target_passed_no_update | withdrawn
    created_at          TEXT NOT NULL
);

CREATE TABLE commitment_updates (
    id             TEXT PRIMARY KEY,
    tenant_id      TEXT NOT NULL,
    commitment_id  TEXT NOT NULL REFERENCES commitments(id),
    kind           TEXT NOT NULL,      -- explicit_revision | completion | reaffirmation | withdrawal
    wording        TEXT NOT NULL,
    location_id    TEXT,
    new_target_text TEXT,
    new_window_end TEXT,
    stated_on      TEXT,
    created_at     TEXT NOT NULL
);

-- ------------------------------------------------------------ peers
CREATE TABLE peer_sets (
    id                 TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    subject_company_id TEXT NOT NULL,
    subject_project_id TEXT,
    name               TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'draft',   -- draft | approved
    approved_by        TEXT,
    approved_at        TEXT,
    approval_rationale TEXT NOT NULL DEFAULT '',
    created_by         TEXT NOT NULL,
    created_at         TEXT NOT NULL
);

CREATE TABLE peer_members (
    id                 TEXT PRIMARY KEY,
    tenant_id          TEXT NOT NULL,
    peer_set_id        TEXT NOT NULL REFERENCES peer_sets(id),
    company_id         TEXT NOT NULL,
    project_id         TEXT,
    classification     TEXT NOT NULL,   -- strict_peer | broader_comparator
    inclusion_reasons  TEXT NOT NULL DEFAULT '[]',
    differences        TEXT NOT NULL DEFAULT '[]',
    decision           TEXT NOT NULL DEFAULT 'proposed',  -- proposed | approved | excluded
    decision_rationale TEXT NOT NULL DEFAULT '',
    decided_by         TEXT,
    decided_at         TEXT
);

CREATE TABLE comparison_snapshots (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    peer_set_id      TEXT NOT NULL,
    market_data_date TEXT NOT NULL,
    body             TEXT NOT NULL,
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    stale            INTEGER NOT NULL DEFAULT 0,
    stale_reason     TEXT NOT NULL DEFAULT ''
);

-- ------------------------------------------------------------ thesis & memo
CREATE TABLE theses (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, company_id TEXT NOT NULL,
    title TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE thesis_versions (
    id                  TEXT PRIMARY KEY,
    tenant_id           TEXT NOT NULL,
    thesis_id           TEXT NOT NULL REFERENCES theses(id),
    version_no          INTEGER NOT NULL,
    thesis_text         TEXT NOT NULL,
    counter_thesis_text TEXT NOT NULL,
    created_by          TEXT NOT NULL,
    created_at          TEXT NOT NULL
);

CREATE TABLE thesis_assumptions (
    id                TEXT PRIMARY KEY,
    tenant_id         TEXT NOT NULL,
    thesis_version_id TEXT NOT NULL,
    text              TEXT NOT NULL,
    company_id        TEXT NOT NULL,
    project_id        TEXT,
    metric_ids        TEXT NOT NULL DEFAULT '[]',
    fact_ids          TEXT NOT NULL DEFAULT '[]',
    calc_ids          TEXT NOT NULL DEFAULT '[]',
    commitment_ids    TEXT NOT NULL DEFAULT '[]',
    status            TEXT NOT NULL DEFAULT 'holding',  -- holding | affected_by_change | under_review | no_longer_supported
    status_reason     TEXT NOT NULL DEFAULT '',
    updated_at        TEXT NOT NULL
);

CREATE TABLE memos (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, company_id TEXT NOT NULL,
    title TEXT NOT NULL, thesis_id TEXT, peer_set_id TEXT,
    created_by TEXT NOT NULL, created_at TEXT NOT NULL
);

-- An approved memo version is immutable. Later edits create a new version.
CREATE TABLE memo_versions (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    memo_id         TEXT NOT NULL REFERENCES memos(id),
    version_no      INTEGER NOT NULL,
    status          TEXT NOT NULL,      -- draft | in_review | approved | superseded
    body            TEXT NOT NULL,
    author          TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    submitted_at    TEXT,
    approved_by     TEXT,
    approved_at     TEXT,
    content_sha256  TEXT,
    evidence_cutoff TEXT,
    stale           INTEGER NOT NULL DEFAULT 0,
    stale_reason    TEXT NOT NULL DEFAULT ''
);

-- ------------------------------------------------------------ monitoring
CREATE TABLE events (
    id                TEXT PRIMARY KEY,
    tenant_id         TEXT NOT NULL,
    company_id        TEXT,
    project_id        TEXT,
    kind              TEXT NOT NULL,
    title             TEXT NOT NULL,
    detail            TEXT NOT NULL DEFAULT '{}',
    source_version_id TEXT,
    event_date        TEXT,
    dedupe_key        TEXT,
    duplicate_of      TEXT,
    status            TEXT NOT NULL DEFAULT 'new',   -- new | reviewed | dismissed | resolved
    status_reason     TEXT NOT NULL DEFAULT '',
    reviewed_by       TEXT,
    reviewed_at       TEXT,
    created_at        TEXT NOT NULL
);
CREATE INDEX events_tenant ON events(tenant_id, created_at);

CREATE TABLE event_links (
    tenant_id  TEXT NOT NULL,
    event_id   TEXT NOT NULL,
    kind       TEXT NOT NULL,
    target_id  TEXT NOT NULL,
    PRIMARY KEY (tenant_id, event_id, kind, target_id)
);

CREATE TABLE notifications (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, user_id TEXT,
    event_id TEXT, message TEXT NOT NULL, created_at TEXT NOT NULL, read_at TEXT
);

CREATE TABLE watchlists (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
    created_by TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE watchlist_members (
    tenant_id TEXT NOT NULL, watchlist_id TEXT NOT NULL, company_id TEXT NOT NULL,
    added_at TEXT NOT NULL, PRIMARY KEY (watchlist_id, company_id)
);

CREATE TABLE holdings (
    id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, portfolio TEXT NOT NULL,
    company_id TEXT NOT NULL, shares TEXT NOT NULL, as_of_date TEXT NOT NULL,
    created_by TEXT NOT NULL, created_at TEXT NOT NULL
);

CREATE TABLE source_feeds (
    id                       TEXT PRIMARY KEY,
    tenant_id                TEXT NOT NULL,
    name                     TEXT NOT NULL,
    kind                     TEXT NOT NULL,     -- upload | connector
    status                   TEXT NOT NULL,     -- active | not_configured | failed
    last_success_at          TEXT,
    last_attempt_at          TEXT,
    last_error               TEXT NOT NULL DEFAULT '',
    refresh_expectation_days INTEGER,
    licensing_note           TEXT NOT NULL DEFAULT ''
);

-- ------------------------------------------------------------ usage & exports
CREATE TABLE usage_ledger (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    at         TEXT NOT NULL,
    kind       TEXT NOT NULL,   -- document_processed | pages_parsed | storage_bytes | model_call | reviewer_action | export
    quantity   TEXT NOT NULL,
    unit       TEXT NOT NULL DEFAULT '',
    model      TEXT,
    tokens_in  INTEGER,
    tokens_out INTEGER,
    cost_usd   TEXT,
    detail     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE exports (
    id             TEXT PRIMARY KEY,
    tenant_id      TEXT NOT NULL,
    kind           TEXT NOT NULL,
    target_id      TEXT NOT NULL,
    target_version TEXT,
    fmt            TEXT NOT NULL,
    status_label   TEXT NOT NULL,
    sha256         TEXT NOT NULL,
    created_by     TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

-- ------------------------------------------------------------ audit
-- Append-only. Each row carries SHA-256(previous chain || canonical payload).
CREATE TABLE audit (
    seq       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT '',
    actor     TEXT NOT NULL,
    role      TEXT NOT NULL,
    action    TEXT NOT NULL,
    target    TEXT NOT NULL DEFAULT '',
    detail    TEXT NOT NULL DEFAULT '',
    count     INTEGER NOT NULL DEFAULT 0,
    chain     TEXT NOT NULL
);
