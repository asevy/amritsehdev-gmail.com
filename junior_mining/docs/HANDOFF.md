# Handoff

Branch: `claude/zen-bell-7zcp1k` of `asevy/amritsehdev-gmail.com`. All new work
is under `junior_mining/`. No existing file outside it was modified, and no
other repository was changed (the other repositories were cloned read-only for
inspection).

## Runnable commands
```bash
cd junior_mining
pip install -r requirements.txt
python -m pytest                                   # 144 tests
python scripts/demo.py                             # end-to-end over HTTP; writes docs/DEMO_TRANSCRIPT.md
python -m jmi.bench benchmark/dev_synthetic_questions.jsonl
JMI_DATA_DIR=./data python -m jmi seed-demo && JMI_DATA_DIR=./data python -m jmi serve
python scripts/export_contracts.py                 # regenerate docs/contracts/*.json
```

## Files added
- `jmi/` — 32 Python modules (≈9,800 lines): see the module map in ARCHITECTURE.md
- `jmi/migrations/001_core.sql` — canonical schema; `002_api_tokens.sql` — connector tokens (hash only)
- `fixtures/synthetic.py` — deterministic SYNTHETIC document generator
- `tests/` — 21 test files, 144 tests (`test_01`…`test_16` = brief §17 cases; 3 files for the Claude integration)
- `scripts/demo.py`, `scripts/export_contracts.py`
- `benchmark/PROPOSAL.md`, `benchmark/dev_synthetic_questions.jsonl`
- `docs/` — CLAUDE_INTEGRATION, REUSE_INVENTORY, ARCHITECTURE, PRODUCT_SPEC, DATA_CONTRACTS (+ `contracts/`),
  CALCULATIONS, DATA_SOURCES, TEST_RESULTS, DEMO_TRANSCRIPT, FEATURE_MATRIX, RUNBOOK,
  DEPLOY, HANDOFF, `screenshots/`
- `README.md`, `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`

## Known limitations (read before relying on anything)
1. **Validated only on synthetic fixtures** written alongside the rules. Recall
   and precision on real NI 43-101 / S-K 1300 / JORC documents are unknown.
2. **Extraction is rule-based** and phrase-sensitive; real disclosures will
   produce more `needs_review` items and missed candidates. Unruled PDF tables
   are not detected. No OCR.
3. **Definitions registry not reviewed** by a qualified person or disclosure
   specialist; not a compliance opinion.
4. **No live connectors** (SEDAR+, EDGAR, market data, registries); market data
   enters only as uploaded files.
5. **Claude API features are untested against the live API** (no key here; fake client only) and off by default. The Claude connector is tested over real stdio.
6. **Single-node SQLite**, requests serialised; no MFA/SSO; not penetration-tested;
   not deployed.
7. Q&A intent matching is keyword-based; questions outside the metric list get
   passages-only or not-found responses by design.
8. The medlegal / IME system, the "Counsel Workbench" (`wb_auth`) and the MINSA
   program were not available to this session; nothing from them is reused or
   claimed (REUSE_INVENTORY.md).
9. Competitor capability recheck blocked by network policy.

## Next concrete integration tasks
0. Claude: live smoke test with a firm's Anthropic API key; measure Claude proposals against the rule baseline on real documents; decide on a hosted claude.ai connector (HTTPS + OAuth). See CLAUDE_INTEGRATION.md.
1. Attach the IME / Counsel Workbench and MINSA repositories if they exist, and
   extend the reuse inventory (e.g. compare `wb_auth` with `jmi/auth.py`).
2. Obtain 5–10 real, lawfully obtained technical reports and MD&As; run
   ingestion; log every miss as a rule defect or a definition question.
3. Specialist review of `jmi/definitions.py` and `jmi/diligence.ITEMS`; add
   S-K 1300 / JORC category and terminology mappings.
4. Expert-labelled benchmark per `benchmark/PROPOSAL.md` with held-out companies.
5. EDGAR adapter (public, rate-limited) behind `ingest.upload`; review SEDAR+
   terms before any automation.
6. OCR engine for scanned pages, with OCR text marked as such and always
   routed to review.
7. Record each firm's Anthropic data-retention configuration before enabling
   Claude features for it; compare Claude proposals against the deterministic
   baseline on the benchmark (task 0).
8. TLS reverse proxy, off-host backups, MFA/SSO, security review, then a
   closed pilot with one tenant.
9. Extract a shared auth/audit library only if Vision//Edge and this product
   both adopt it, with separate release checks.
