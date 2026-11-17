-- RECLAIM platform store (commercial company; PIPEDA).
-- Holds accounts, memberships, coaching data, form checks, partner credits,
-- marketing/demand-test data. It never holds clinical records or dispensing records:
-- those live in clinical.db and pharmacy.db, linked only by users.patient_ref.

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  pw_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('member','coach','clinician','pharmacist','admin')),
  province TEXT,
  patient_ref TEXT UNIQUE,            -- opaque link to clinical/pharmacy stores
  sponsor_code TEXT,                   -- employer sponsorship, if any
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,                 -- sha256 of the cookie token
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL
);

-- Append-only consent ledger. Current state = latest row per (user, kind).
CREATE TABLE IF NOT EXISTS consents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  granted INTEGER NOT NULL CHECK (granted IN (0,1)),
  version TEXT NOT NULL,
  text_sha TEXT NOT NULL,              -- hash of the exact wording shown
  route TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Platform orders only. Medical fees and medication are sold by other entities in other stores.
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  entity_id TEXT NOT NULL DEFAULT 'platform' CHECK (entity_id = 'platform'),
  status TEXT NOT NULL CHECK (status IN ('pending','paid','refunded','failed')),
  province TEXT NOT NULL,
  subtotal_cents INTEGER NOT NULL,
  tax_cents INTEGER NOT NULL,
  total_cents INTEGER NOT NULL,
  currency TEXT NOT NULL DEFAULT 'CAD',
  price_variant INTEGER NOT NULL DEFAULT 0,
  sponsor_code TEXT,
  agreement_json TEXT,                 -- Consumer Protection Act internet-agreement snapshot
  agreement_sha TEXT,
  provider TEXT,
  provider_ref TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  paid_at TEXT
);

CREATE TABLE IF NOT EXISTS order_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT NOT NULL REFERENCES orders(id),
  sku TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('plan','addon')),
  description TEXT NOT NULL,
  qty INTEGER NOT NULL DEFAULT 1,
  unit_cents INTEGER NOT NULL,
  tax_code TEXT NOT NULL CHECK (tax_code IN ('taxable_service','taxable_goods')),
  tax_cents INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS refunds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id TEXT NOT NULL REFERENCES orders(id),
  amount_cents INTEGER NOT NULL,
  policy_rule TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active','paused','cancelled')),
  price_cents INTEGER NOT NULL,
  price_variant INTEGER NOT NULL DEFAULT 0,
  sponsored INTEGER NOT NULL DEFAULT 0,
  order_id TEXT,
  started_at TEXT NOT NULL,
  current_period_end TEXT NOT NULL,
  cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
  paused_until TEXT,
  cancel_reason TEXT,
  cancelled_at TEXT
);

CREATE TABLE IF NOT EXISTS credits_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  delta INTEGER NOT NULL,
  reason TEXT NOT NULL,
  ref TEXT,
  expires_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Coaching side of the Blueprint (versioned). Clinical history is NOT stored here.
CREATE TABLE IF NOT EXISTS blueprints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  data_json TEXT NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('assessment','coach','member')),
  author TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (user_id, version)
);

CREATE TABLE IF NOT EXISTS measurements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('self','coach','partner_scan','device')),
  measured_at TEXT NOT NULL,
  note TEXT
);

CREATE TABLE IF NOT EXISTS plan_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  week_start TEXT NOT NULL,
  day INTEGER NOT NULL CHECK (day BETWEEN 0 AND 6),
  kind TEXT NOT NULL CHECK (kind IN ('training','nutrition','habit','lesson','test')),
  title TEXT NOT NULL,
  detail TEXT,
  form_exercise TEXT,                  -- a form-check task: ticks when a clip for this exercise arrives
  done_at TEXT
);

-- Form-check videos: the member's own clips, reviewed by their coach. Videos are sensitive personal
-- information: stored privately (never under /public), streamed only via short-lived signed links,
-- visible only to the member and coaches, deletable by the member at any time.
CREATE TABLE IF NOT EXISTS form_checks (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  exercise TEXT NOT NULL,
  file_path TEXT,                      -- NULL when the member shared measurements only, or deleted the video
  mime TEXT,
  size_bytes INTEGER,
  member_note TEXT,
  recorded_by TEXT NOT NULL DEFAULT 'member' CHECK (recorded_by IN ('member','coach')),
  recorded_by_id TEXT NOT NULL,
  mechanics_json TEXT,                 -- on-device pose estimates (angles, reps, tempo)
  status TEXT NOT NULL CHECK (status IN ('submitted','reviewed','deleted')),
  created_at TEXT NOT NULL,
  reviewer_id TEXT,
  reviewed_at TEXT,
  scores_json TEXT,                    -- coach rating per criterion: 1 needs work, 2 improving, 3 solid
  cues TEXT
);

-- Coach and partner bookings. Clinical visits are booked in clinical.db.
CREATE TABLE IF NOT EXISTS bookings (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('coach','partner')),
  partner_id TEXT,
  title TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  duration_min INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('booked','cancelled','completed','no_show')),
  credits_used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Coaching messages only. Clinical messages are in clinical.db.
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,              -- the member the thread belongs to
  sender_id TEXT NOT NULL,
  sender_role TEXT NOT NULL CHECK (sender_role IN ('member','coach')),
  sender_name TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS waitlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  jurisdiction TEXT NOT NULL,
  fsa TEXT,                            -- first 3 chars of postal code only
  interests_json TEXT,
  marketing_consent INTEGER NOT NULL DEFAULT 0,
  consent_text_sha TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL CHECK (kind IN ('employer','enterprise','partner','research')),
  org TEXT NOT NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  size TEXT,
  message TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- First-party product analytics. Property keys are allow-listed in lib/analytics.ts; no health data.
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  anon_id TEXT,
  user_id TEXT,
  name TEXT NOT NULL,
  props_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Van Westendorp price-sensitivity responses (monthly coaching, CAD).
CREATE TABLE IF NOT EXISTS wtp_responses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  anon_id TEXT,
  too_cheap INTEGER NOT NULL,
  cheap INTEGER NOT NULL,
  expensive INTEGER NOT NULL,
  too_expensive INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  to_email TEXT NOT NULL,
  user_id TEXT,
  entity_id TEXT NOT NULL,
  class TEXT NOT NULL CHECK (class IN ('transactional','commercial')),
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS data_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('export','deletion','correction','access')),
  status TEXT NOT NULL DEFAULT 'open',
  due_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sponsors (
  code TEXT PRIMARY KEY,
  org_name TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  seats INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Tamper-evident, append-only audit log (hash chained).
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id TEXT,
  actor_role TEXT,
  subject_user TEXT,
  action TEXT NOT NULL,
  resource TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;

CREATE INDEX IF NOT EXISTS idx_measurements_user ON measurements(user_id, metric, measured_at);
CREATE INDEX IF NOT EXISTS idx_form_checks_user ON form_checks(user_id, exercise, created_at);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(name, created_at);
CREATE INDEX IF NOT EXISTS idx_consents_user ON consents(user_id, kind, id);
