-- Pharmacy store: belongs to the licensed pharmacy (its own PHIPA custodian and merchant of record).
-- In production this is the pharmacy's dispensing system. Only prescriptions a patient chose to
-- send to this pharmacy ever arrive here.

CREATE TABLE IF NOT EXISTS patients (
  patient_ref TEXT PRIMARY KEY,
  legal_name TEXT NOT NULL,
  dob TEXT,
  delivery_address TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Pharmacy's own price list. Prices depend on product and quantity only — never on membership.
CREATE TABLE IF NOT EXISTS price_list (
  din TEXT PRIMARY KEY,
  pack_desc TEXT NOT NULL,
  drug_cost_cents INTEGER NOT NULL,
  dispensing_fee_cents INTEGER NOT NULL,
  delivery_cents INTEGER NOT NULL,
  cold_chain INTEGER NOT NULL DEFAULT 0,
  demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rx_inbox (
  id TEXT PRIMARY KEY,
  prescription_id TEXT UNIQUE NOT NULL,
  patient_ref TEXT NOT NULL,
  din TEXT NOT NULL,
  display_name TEXT NOT NULL,
  sig TEXT NOT NULL,
  quantity TEXT NOT NULL,
  refills_authorised INTEGER NOT NULL,
  received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fills (
  id TEXT PRIMARY KEY,
  rx_id TEXT NOT NULL REFERENCES rx_inbox(id),
  patient_ref TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('requested','verified','awaiting_payment','paid','shipped','delivered','cancelled')),
  pharmacist_id TEXT,
  counselled_at TEXT,
  insurance_status TEXT NOT NULL DEFAULT 'not_submitted' CHECK (insurance_status IN ('not_submitted','adjudicated','rejected','cash')),
  drug_cents INTEGER,
  dispensing_fee_cents INTEGER,
  delivery_cents INTEGER,
  plan_pays_cents INTEGER NOT NULL DEFAULT 0,
  patient_total_cents INTEGER,
  tracking TEXT,
  requested_at TEXT NOT NULL DEFAULT (datetime('now')),
  paid_at TEXT,
  shipped_at TEXT
);

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  fill_id TEXT NOT NULL REFERENCES fills(id),
  patient_ref TEXT NOT NULL,
  entity_id TEXT NOT NULL DEFAULT 'pharmacy' CHECK (entity_id = 'pharmacy'),
  total_cents INTEGER NOT NULL,
  tax_cents INTEGER NOT NULL DEFAULT 0 CHECK (tax_cents = 0), -- prescription drugs are zero-rated
  status TEXT NOT NULL CHECK (status IN ('paid','refunded')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

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
