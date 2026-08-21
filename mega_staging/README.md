# mega_staging/  —  Phase 1 files, staging for `asevy/investing-alerts`

**These files do NOT belong in this repo long-term.** They are staged here
because this sandbox session cannot push directly to `asevy/investing-alerts`
(different scope). Migrate them into `~/investing/` on the MacBook.

## What's here

| File | Purpose | Migrate to |
|---|---|---|
| `PHASE_1_SPEC.md` | Precise spec the MacBook Claude Code session implements | `~/investing/docs/` |
| `ntfy_publish.py` | Ntfy helper with priority + action-button wrappers | `~/investing/` |
| `orchestrator_skeleton.py` | Dispatch pattern for analysts → digest → push. Runs a synthetic self-test offline | `~/investing/` |

## Migration steps (5 minutes on the MacBook)

```
cd ~/Documents
git clone https://github.com/asevy/amritsehdev-gmail.com.git amritsehdev-staging
cd amritsehdev-staging
git checkout claude/mega-system-phase1-staging
cp mega_staging/PHASE_1_SPEC.md ~/investing/docs/
cp mega_staging/ntfy_publish.py ~/investing/
cp mega_staging/orchestrator_skeleton.py ~/investing/
cd ~/investing
# then open Claude Code and follow PHASE_1_SPEC.md
```

## Constraints these files respect

- **Do not modify** `quality_value_screener.py` or `alpha_screener.py` (methodology freeze until July 20 2027).
- **Do not push notifications from here.** ntfy.sh is blocked from this
  sandbox — the ntfy helper was written to a spec and tested only against
  a mock stub. The MacBook agent must verify the wire before enabling
  cron pushes.
- **The Master_Watchlist grade format** (`B 74 ADBE   B:B A:B- D:A-`) is
  preserved — the mega-system digest wraps the existing screener output,
  it does not reformat it.
