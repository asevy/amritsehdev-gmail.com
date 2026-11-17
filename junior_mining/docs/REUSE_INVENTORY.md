# Reuse inventory — Junior Mining Intelligence

Audit date: 2026-11-17. Every row below was produced by cloning and reading the
repository named, and — where tests exist — by running them in a scratch copy.
Nothing here relies on memory of earlier sessions. Earlier discussions are not
evidence of current status.

## What was available

| Repository (GitHub, `asevy/…`) | State on 2026-11-17 | Relevance |
|---|---|---|
| `amritsehdev-gmail.com` (this repo, branch `claude/zen-bell-7zcp1k`) | Swing-trading toolkit, 13 Python files | One concept reused (disclosure-language patterns); scoring modules excluded |
| `vision-edge-gateway` @ `592cbff` | Vision//Edge (Eyeology) deploy repo: stdlib server, auth, SQLite data layer, 10 test files | **Primary implementation asset** |
| `mso-ip-lab` @ `a1b3fd4` | MSO IP Lab (Eyeology + MPC): Python package, SQL migrations, audit log, cost ceiling, 168 tests | Migration runner, usage/cost instrumentation pattern |
| `investing-alerts` @ `e3aefb4` | Screeners with `score_*` / `grade()` functions | Excluded (scores and grades) |
| `nextjs-boilerplate` @ `cb43788` | Unmodified create-next-app template (Next 15.5, React 19) | Excluded (no application logic) |
| `ltfesi-prognosis-agent`, `ltfesi-prognosis-agent_1` | **Empty repositories** — no commits, no branches | Nothing to reuse |

**Unavailable — stated exactly:**

* **The medlegal / IME system and the "Counsel Workbench"** are not in any
  repository this session can reach (`list_repos` returns the 8 above; none is
  named IME, medlegal, counsel or workbench). `vision-edge-gateway/ve_auth.py:3`
  and `SECURITY.md:3` refer to "the Counsel Workbench's `wb_auth`" — that module
  is not present anywhere accessible. A code-only Google Drive search for
  `Counsel Workbench`, `wb_db`, `ime_server` returned nothing. (A broader Drive
  search returned patient records; none was opened or used, per brief §14.)
* **The MINSA program** — not found in any accessible repository or code search.
* **The Vision//Edge build pipeline** — `SECURITY.md` documents `build.py --seed`
  and a `server/` directory; neither is in the deploy repo. Four of its test
  files depend on files that only that pipeline produces (see below).

If those codebases exist elsewhere, attaching them to a session would let this
inventory be extended. No reuse from them is claimed.

## Inventory

Legend for **Evidence**: *tested* = tests exist and were run here and passed;
*tested-partial* = some tests could not run; *untested* = code exists, no tests
ran; *design-only* = documentation without code.

| Component | Exact repository and path | Behaviour (as read) | Evidence | Reuse decision | Limitations |
|---|---|---|---|---|---|
| Password auth, sessions, lockout | `vision-edge-gateway/ve_auth.py` (`Auth`, `Actor`) | scrypt n=2¹⁴ r=8 p=1 with per-user salt; constant-time compare; missing user still hashed (timing); 12-char minimum; 5 failures/15 min lockout; opaque session tokens, 8 h TTL; password change invalidates sessions | *tested* — `test_e2e.py` 45/45 and `test_redteam.py` 26/26 pass over real HTTP | **Adapt** → `jmi/auth.py`: roles replaced (admin/analyst/reviewer/read_only), users and sessions moved into SQLite with a `tenant_id`, file storage dropped | Clinical role model not applicable; no MFA/SSO; sessions in-process |
| Per-record authorisation | `vision-edge-gateway/ve_db.py` `Store._scope()` (l.452) | Derives a SQL predicate from the actor; **raises** on an unknown role rather than widening; cross-org records return 404 not 403 | *tested* — `test_ve_db.py` 54/54, `test_e2e.py` | **Adapt** → `jmi/store.py` `Store._scope()`: tenant predicate on every query, same raise-on-unknown rule, same 404 rule | Org model was single-tenant-with-orgs; here tenant is the hard boundary |
| Tamper-evident audit chain | `vision-edge-gateway/ve_db.py` `Store.audit()`, `verify_chain()` (l.410–441) | Each row stores SHA-256(previous chain ‖ canonical payload); reads audited as well as writes; `verify_chain` names first broken row | *tested* — `test_ve_db.py`, `test_rc2_adversarial.py` 51/51 | **Adapt** → `jmi/audit.py`: adds `tenant_id`, export/version identifiers; chain logic unchanged | Append-only by convention + hash, not WORM storage |
| Transactions, WAL, backup/restore | `vision-edge-gateway/ve_db.py` `_tx()`, `backup()`, `restore()` (l.398, 2322–2367) | `BEGIN IMMEDIATE`; WAL + `synchronous=FULL`; consistent online backup; restore refuses a backup failing `integrity_check` | *tested* (restore drill in `SECURITY.md`; `test_ve_db.py`) | **Adapt** → `jmi/db.py` | Single node SQLite |
| HTTP hardening | `vision-edge-gateway/ve_server.py` `Handler._send()`, `do_POST()` | CSP, `X-Frame-Options: DENY`, `nosniff`, `no-store`; JSON writes require session cookie **and** a session-bound CSRF header; body size cap; data-layer exceptions mapped to 403/404 without detail | *tested* — `test_e2e.py` | **Adapt** → `jmi/server.py` | stdlib `http.server`; needs TLS proxy in front |
| Payload-level boundary tests | `vision-edge-gateway/test_boundary.py` (`walk()`) | Asserts on the raw serialised payload, never rendered HTML | *tested* — 56/56 | **Adapt pattern** → `tests/test_no_scores.py`, `tests/test_tenant_isolation.py` walk raw API/export payloads | — |
| Protocol-version handling | `vision-edge-gateway/ve_db.py` `certifications`, `certification_in_force()` (l.364–377, 2018–2036) | History-not-flag: each grant is a row with validity window and `protocol_versions`; a record is stamped with the grant in force on its date | *tested* — `test_gate24_regression.py` 64/64 | **Adapt the principle** → definition registry is versioned and every fact/calculation is stamped with the definition/formula version in force | Domain-specific; code not copied |
| Clinical firewall / de-identification | `vision-edge-gateway/ve_db.py` `_project()`, `_firewall_*`, k-anonymity | Field-level projection by role before serialisation | *tested* | **Not reused** — clinical domain; brief §16 excludes clinical functionality. Principle (project on the way out) informs the export layer | — |
| Platform UI | `vision-edge-gateway/app/vision-edge-demo.html` (15,330 lines) | Single-file clinical SPA | *tested-partial* — `test_analytics.py`, `test_gate6a.py`, `test_workflow_render.py` fail: `FileNotFoundError: vision-edge.html`; `test_promises.py` fails: `consent-packet.html` — the build outputs are absent from the deploy repo | **Not reused** | Build pipeline (`build.py`) not available |
| Numbered SQL migrations | `mso-ip-lab/src/mso_ip_lab/storage/db.py` `migrate()` + `storage/migrations/001_initial.sql` | `schema_migrations` table; files applied in lexical order; failed migration leaves no marker | *tested* — `tests/test_storage_db.py` within 168/168 passing (`uv run pytest`) | **Adapt** → `jmi/db.py` `migrate()` (same contract, migration applied inside a transaction) | — |
| LLM/usage audit with cost | `mso-ip-lab/src/mso_ip_lab/storage/audit.py` `log_call()`; `pipeline/cost.py` | Records actor, action, model, tokens, USD cost per call; per-run cost ceiling raises | *tested* — `tests/test_storage_audit.py` | **Adapt** → `jmi/usage.py` usage ledger (documents, pages, model calls, tokens, cost, storage, reviewer actions) | Prices are config, not validated |
| Opportunity scorer | `mso-ip-lab/src/mso_ip_lab/agents/scorer.py` | Weighted scores | *tested* | **Excluded** — brief §2 forbids scoring | — |
| Disclosure-language patterns | `amritsehdev-gmail.com/filing_forensics.py` `FLAG_RULES` (l.109) | Regexes for going-concern, material weakness, restatement, auditor change, late filing, dilution language; returns excerpt + offset | *untested* (self-test prints only; no assertions) | **Adapt concept** → `jmi/extract.py` disclosure signals. **Severity weights and `risk_score` dropped**; matches create open diligence questions, never grades | Patterns are US-centric (10-K); Canadian "material uncertainty" wording added |
| Cite-or-N/A prompt | `amritsehdev-gmail.com/filing_forensics.py` `CITE_SYSTEM`, `ask_filing()` | Instructs a model to quote or answer N/A | *untested* | **Superseded** — a prompt instruction is not a control. `jmi/answers.py` answers only from stored facts and validates citations in code | Requires API key; not available here |
| Swing scanner / pipeline / screeners | `amritsehdev-gmail.com/swing_scanner.py`, `swing_pipeline.py`; `investing-alerts/*.py` | Composite scores, grades, rankings | — | **Excluded** — scoring | — |
| Next.js template | `nextjs-boilerplate/app/*` | Default template page | *untested* | **Excluded** — adds a Node toolchain for no reused logic | — |

## Stack decision

The supported, tested stack in the inspected repositories is **Python + stdlib
HTTP server + SQLite** (Vision//Edge) with **numbered SQL migrations and pytest**
(mso-ip-lab). The mining product uses the same stack:

* Python 3.13, `sqlite3` (WAL, FTS5 for derived search indexes), stdlib `http.server`.
* Parsing adapters use libraries already present in the environment:
  `pdfplumber` (text, tables, word coordinates), `pypdfium2` (page images),
  `openpyxl` (XLSX), `reportlab` (PDF export and synthetic fixtures).
  Each adapter reports "dependency unavailable" instead of producing output if
  its library is missing.
* No OCR engine is installed (`tesseract` absent). Pages without a text layer
  are detected and reported as unreadable; they are never guessed at.
* No model provider SDK or key is configured. The model-proposal boundary is
  implemented and tested with a fake model; the default extractor is
  deterministic.

## Isolation

The product lives in `junior_mining/` inside this repository, with its own
package (`jmi`), tests, fixtures and documentation. No file of the swing
toolkit, Vision//Edge or mso-ip-lab was modified. Adapted code was copied with a
provenance header naming the source path and commit, rather than imported, so
the clinical products are not coupled to mining release checks and vice versa.
Extracting a shared library is deferred until a second consumer needs it (see
`HANDOFF.md`).
