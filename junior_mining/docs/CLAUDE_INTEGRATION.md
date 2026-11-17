# Claude integration

Two directions, both optional, both under the firm's control.

| Direction | What the analyst gets | Uses | Status |
|---|---|---|---|
| **The app inside Claude** (connector) | Ask about the firm's evidence records from Claude Desktop or Claude Code: approved facts with quotes, coverage, risks, comparisons, memos, constrained Q&A | The firm's Claude plan (seats); a read-only personal token for this app | Implemented and tested over real stdio with the MCP client SDK |
| **Claude inside the app** (API) | Claude proposes extra fact candidates, routes questions to the right records, drafts memo claims — all still validated and reviewer-approved | An Anthropic **API key** from the firm's Anthropic Console organization | Implemented and tested with a fake client. **No live API call has been made** (no key in this environment) |

**Plans vs API keys.** A claude.ai Pro, Team or Enterprise seat lets people use
Claude (including connectors) but is not API access. "Claude inside the app"
calls the Anthropic API, which needs an API key from the Anthropic Console (or
the firm's existing API arrangement) and is billed per token, separately from
seats. Each firm should use its own key so its own agreement, data-retention
settings and spend apply.

## 1. The app inside Claude (connector)

1. Each user creates a personal token: web app → **Account & Claude connector**
   → *Create connector token* (shown once), or
   `python -m jmi create-api-token <user> --label "Claude Desktop"`.
2. **Claude Desktop** → Settings → Developer → Edit config:
   ```json
   {"mcpServers": {"junior-mining": {
       "command": "python", "args": ["-m", "jmi", "mcp"],
       "cwd": "/path/to/junior_mining",
       "env": {"JMI_DATA_DIR": "/path/to/data", "JMI_API_TOKEN": "jmit_..."}}}}
   ```
   **Claude Code:** `claude mcp add junior-mining --env JMI_DATA_DIR=/path/to/data --env JMI_API_TOKEN=jmit_... -- python -m jmi mcp`
3. In Claude: "Using junior-mining, what does Halvard Peak report for after-tax NPV, and from which document?"

Tools (all annotated read-only): `list_companies`, `get_facts`, `ask`,
`get_coverage`, `get_risks`, `get_comparison`, `get_memo`, `search_documents`,
`list_definitions`.

Controls: the token acts as its user in that user's workspace with **read**
capability only, whatever the user's role; every call is tenant-scoped (another
firm's record is "not found") and audited as the user; facts default to
reviewer-approved and carry their state, evidence type, attribution, dates and
exact source quote; `ask` is the same constrained answerer as the web app; every
result passes the no-score policy scan. Server instructions tell Claude to
attribute issuer statements, keep qualifiers, treat "not found" as unknown and
not to invent scores or recommendations — instructions guide Claude; the
read-only, tenant-scoped data access is what is enforced.

**Not built:** a hosted connector for claude.ai in the browser. That needs a
public HTTPS deployment of the MCP server with connector sign-in (OAuth), which
requires deployment decisions outside this pilot. The stdio connector works
wherever the data directory is reachable (a firm workstation or VDI).

## 2. Claude inside the app (API)

Enable per firm (administrator): web app → **Claude settings**, or
`python -m jmi claude-settings <tenant> --enable --api-key-env JMI_ANTHROPIC_KEY_FIRM_A`.
Put the key in that environment variable through the deployment's secret
manager. Only the variable's **name** is stored; the key never enters the
database, logs or audit.

| Feature | Where | What Claude returns | What still decides |
|---|---|---|---|
| Candidate proposals | Document page button, or automatically after upload (setting) | Structured candidates: metric, exact quote, printed value, unit/scale/currency tokens, dates, qualifiers | Quote must exist verbatim; same independent validation as rule candidates; duplicates of rule extractions skipped; reviewer approval |
| Question routing | Ask page and connector `ask` | Metric ids + qualifiers, or an out-of-scope category | Deterministic refusals run first; the answer is assembled only from stored facts; Claude writes no answer text |
| Memo drafting | Memo page button (draft versions) | Claims citing record ids | Unknown ids dropped; each claim validated as a complete claim; unsupported drafts withheld; reviewer approves each claim |

Request conventions (from the Claude API reference bundled with this session,
2026-11): model `claude-opus-5-5` (configurable); adaptive thinking is always on
for this model and depth is set with `output_config.effort` (`high` for
extraction and drafting, `low` for routing); structured outputs via
`output_config.format` (JSON schema with `additionalProperties: false`);
**server-side refusal fallbacks enabled** with `fallbacks: "default"` and beta
`server-side-fallback-2026-07-01` (not sent for Haiku, which has none); the stable
system prompt is cached; requests stream and `stop_reason` is checked before any
content is read — `refusal` and `max_tokens` store nothing.

Long calls run on a background thread with no database transaction open, so one
firm's Claude call does not block other users; failures become inbox events.

Record keeping: each call adds a usage-ledger row (model actually served, input
and output tokens, estimated cost at list price — Anthropic billing is the source
of truth) and an audit row with purpose, prompt version, requested and served
model, whether a fallback served it, stop reason and request id. Document text
and model reasoning are never stored in either.

Data handling: enabling this sends document text (for proposals) and approved
records (for drafting) to Anthropic's API under the firm's key. Retention,
region and training terms are those of the firm's Anthropic organization and
agreement; this application makes no claim about them. It is off by default.

## Tests
`tests/test_claude_integration.py` (15), `tests/test_mcp_connector.py` (9,
including a real stdio round trip), `tests/test_claude_http.py` (4). They check
request shape, opt-in, firm separation, key never stored, validation gating of
Claude output, refusals/truncation/API errors storing nothing, audit without
document text, background failures surfaced, connector read-only and
tenant-scoped.

## Before relying on it
1. Run a live smoke test with a firm API key (a few cents) and inspect the
   proposals on a real document.
2. Run the benchmark with and without Claude proposals on expert-labelled
   documents and compare precision, recall and reviewer effort per document —
   the deterministic rules are the baseline Claude must beat.
3. Confirm the firm's Anthropic data-retention configuration and record it.
