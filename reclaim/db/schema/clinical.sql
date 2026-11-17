-- Clinical store: belongs to the INDEPENDENT medical practice (PHIPA health information custodian).
-- In production this is the practice's certified EMR; this SQLite file stands in for it so the
-- prototype can demonstrate the boundary. The platform reads/writes here only as the practice's
-- agent / electronic service provider, and every access is written to the audit log below.

CREATE TABLE IF NOT EXISTS patients (
  patient_ref TEXT PRIMARY KEY,
  legal_name TEXT NOT NULL,
  dob TEXT,
  province TEXT NOT NULL,
  hcn_masked TEXT,                     -- health card number (masked in this prototype)
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clinicians (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  designation TEXT NOT NULL CHECK (designation IN ('MD','NP')),
  college TEXT NOT NULL,
  reg_no TEXT NOT NULL,
  licensed_provinces TEXT NOT NULL     -- comma-separated
);

CREATE TABLE IF NOT EXISTS enrolments (
  patient_ref TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('intake_submitted','active','discharged')),
  privacy_notice_sha TEXT NOT NULL,
  virtual_care_consent_sha TEXT NOT NULL,
  enrolled_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS intake (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_ref TEXT NOT NULL,
  answers_json TEXT NOT NULL,
  red_flags_json TEXT NOT NULL,
  submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- OHIP-insured encounters can never carry a patient fee.
CREATE TABLE IF NOT EXISTS encounters (
  id TEXT PRIMARY KEY,
  patient_ref TEXT NOT NULL,
  clinician_id TEXT NOT NULL REFERENCES clinicians(id),
  kind TEXT NOT NULL CHECK (kind IN ('initial','follow_up')),
  modality TEXT NOT NULL CHECK (modality IN ('video','phone')),
  starts_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('booked','completed','cancelled')),
  insured_status TEXT NOT NULL CHECK (insured_status IN ('ohip','uninsured','tbd')),
  fee_cents INTEGER NOT NULL DEFAULT 0,
  location_attested INTEGER NOT NULL CHECK (location_attested = 1),
  note TEXT,
  signed_at TEXT,
  CHECK (insured_status <> 'ohip' OR fee_cents = 0)
);

-- Only Health Canada-authorised, marketed products approved by clinical governance can be prescribed.
CREATE TABLE IF NOT EXISTS formulary (
  id TEXT PRIMARY KEY,
  din TEXT NOT NULL,
  display_name TEXT NOT NULL,
  hc_status TEXT NOT NULL CHECK (hc_status = 'marketed'),
  approved_indication TEXT NOT NULL,
  monitoring TEXT NOT NULL,
  evidence_ref TEXT NOT NULL,
  governance_approved_at TEXT NOT NULL,
  demo INTEGER NOT NULL DEFAULT 0
);

-- One product per prescription; no bundles or "stacks".
CREATE TABLE IF NOT EXISTS prescriptions (
  id TEXT PRIMARY KEY,
  patient_ref TEXT NOT NULL,
  clinician_id TEXT NOT NULL REFERENCES clinicians(id),
  encounter_id TEXT REFERENCES encounters(id),
  formulary_id TEXT NOT NULL REFERENCES formulary(id),
  sig TEXT NOT NULL,
  quantity TEXT NOT NULL,
  refills INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('active','stopped')),
  destination_type TEXT CHECK (destination_type IN ('aligned_pharmacy','other_pharmacy','paper')),
  destination_detail TEXT,
  choice_presented_json TEXT,          -- exactly which options, in which order, the patient saw
  choice_made_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS labs (
  id TEXT PRIMARY KEY,
  patient_ref TEXT NOT NULL,
  panel TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('requisition_issued','resulted')),
  ordered_at TEXT NOT NULL,
  resulted_at TEXT,
  result_summary TEXT,
  clinician_comment TEXT
);

CREATE TABLE IF NOT EXISTS clinical_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_ref TEXT NOT NULL,
  sender TEXT NOT NULL CHECK (sender IN ('patient','clinician')),
  sender_name TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS side_effect_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_ref TEXT NOT NULL,
  description TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('mild','moderate','severe')),
  status TEXT NOT NULL DEFAULT 'new',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- The only clinical content a coach may see, written by a clinician, shared only with patient consent.
CREATE TABLE IF NOT EXISTS care_team_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_ref TEXT NOT NULL,
  coach_safe_text TEXT NOT NULL,
  author_id TEXT NOT NULL,
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
