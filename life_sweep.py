"""
life_sweep.py
=============
The same discipline that ran the money, pointed at the whole life.

The swing toolkit refused to surface a name unless it was sound, and never
emitted a signal without a stop. Life Sweep is the mirror: it refuses to pay a
grade on commitment or planning, only on completion; it never lets a shiny new
idea cut ahead of an open scorecard item; and it caps the whole game at C when
the operator's Health is failing, because the operator is the constraint on
every other domain.

This module is the *enforcer*, not the coach. It holds the state honestly and
computes the mechanics that a human is tempted to fudge:

  - OVERALL GRADE with the HEALTH MULTIPLIER CAP. A failing Health grade caps
    the overall at C, no matter how good Wealth looks. (risk_manager.py capped
    position size; this caps the score.)
  - UNGRADED IS NOT ZERO. Domains with no record are excluded from the overall
    and reported as "no data" — never guessed into a number. (The cite-or-N/A
    rule from filing_forensics, applied to a life.)
  - THE LINE RULE. Nothing below the line scores until something above it closes.
  - STREAKS, boss-risk warning signs, and the weekly sweep, rendered from state.

Grades pay on completion. "Done means" is binary. No partial credit.

State lives in life_state.json (the single source of truth). This file only
reads and renders it; regrading and closing items are judgment calls a human
(or the game master) makes, then writes back.

CLI:
    python life_sweep.py            # self-test on synthetic state, then live board if present
    python life_sweep.py board      # full board from life_state.json
    python life_sweep.py grades     # the monthly grade table
    python life_sweep.py sweep      # the weekly sweep skeleton
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import json
import os
import sys

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "life_state.json")

# Letter <-> points. Academic scale so the overall reads like a report card.
GRADE_POINTS = {
    "A+": 4.3, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F": 0.0,
}
# Failing, in the multiplier sense the command names: an F in Health caps overall at C.
FAILING_GRADES = {"F"}
HEALTH_CAP_GRADE = "C"


def grade_to_points(grade: Optional[str]) -> Optional[float]:
    if grade is None:
        return None
    return GRADE_POINTS.get(grade.strip().upper())


def points_to_grade(points: float) -> str:
    """Nearest letter to a GPA point value."""
    best, best_d = "F", 99.0
    for letter, pts in GRADE_POINTS.items():
        d = abs(pts - points)
        if d < best_d:
            best, best_d = letter, d
    return best


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
def load_state(path: str = STATE_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class Overall:
    grade: str
    computed_from: str          # letters actually used
    ungraded: list              # domains with no data
    health_capped: bool
    note: str


def compute_overall(state: dict) -> Overall:
    """
    Average the GPA of the *graded* domains, convert back to a letter, then apply
    the Health multiplier cap. Ungraded domains are excluded and reported — never
    counted as zero, never guessed into a number.
    """
    domains = state["domains"]
    graded, ungraded = {}, []
    for name in state.get("domain_order", list(domains)):
        d = domains[name]
        pts = grade_to_points(d.get("grade"))
        if d.get("graded") and pts is not None:
            graded[name] = pts
        else:
            ungraded.append(name)

    if not graded:
        return Overall("N/A", "", ungraded, False,
                       "No domains graded yet — overall is undeclared until the first regrade.")

    avg = sum(graded.values()) / len(graded)
    letter = points_to_grade(avg)

    # Health multiplier cap.
    health = domains.get("Health", {})
    capped = False
    if health.get("graded") and (health.get("grade") or "").upper() in FAILING_GRADES:
        if grade_to_points(letter) > grade_to_points(HEALTH_CAP_GRADE):
            letter, capped = HEALTH_CAP_GRADE, True

    note = "Health is the multiplier: capped at %s because Health is failing." % HEALTH_CAP_GRADE \
        if capped else "Health grade is not failing; no cap applied."
    return Overall(letter, ", ".join(sorted(graded)), ungraded, capped, note)


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #
def render_grades(state: dict) -> str:
    d = state["domains"]
    rows = ["  DOMAIN       GRADE  MOV  WHY",
            "  " + "-" * 78]
    for name in state.get("domain_order", list(d)):
        dom = d[name]
        g = dom.get("grade") or "—"
        mov = dom.get("movement") or "→"
        why = dom.get("why", "")
        if len(why) > 60:
            why = why[:57] + "..."
        star = "*" if dom.get("multiplier") else " "
        rows.append("  %-11s%s %-5s %-3s  %s" % (name, star, g, mov, why))
    ov = compute_overall(state)
    rows.append("  " + "-" * 78)
    stated = state.get("meta", {}).get("stated_overall")
    n_graded = len([n for n in d if d[n].get("graded")])
    if stated:
        src = state["meta"].get("stated_overall_source", "operator")
        rows.append("  OVERALL      %-5s      stated by %s" % (stated, src))
        rows.append("  computed     %-5s      provisional off %d/%d graded domains — %s"
                    % (ov.grade, n_graded, len(d), ov.note))
    else:
        rows.append("  OVERALL      %-5s      %s" % (ov.grade, ov.note))
    if ov.ungraded:
        rows.append("  ungraded (excluded, not guessed): " + ", ".join(ov.ungraded))
    rows.append("  * = Health is the multiplier (a failing grade caps overall at %s)" % HEALTH_CAP_GRADE)
    return "\n".join(rows)


def open_items(state: dict) -> list:
    out = []
    for domain, cards in state.get("scorecards", {}).items():
        for c in cards:
            if c.get("status") == "open":
                out.append((domain, c))
    return out


def render_sweep(state: dict) -> str:
    """The weekly-sweep skeleton, populated with what the record actually holds."""
    q = state["meta"]["season"]
    lines = []
    lines.append("WEEKLY SWEEP  (as of %s)" % state["meta"]["as_of"])
    lines.append("Season: %s   Main Quest: %s" % (q["label"], q["main_quest"]))
    lines.append("")

    lines.append("OPEN ITEMS — one next action each (fill the action live):")
    items = open_items(state)
    if not items:
        lines.append("  (none open — declare the next scorecard)")
    for domain, c in items:
        blocked = c.get("blocked_on")
        tag = ("  [BLOCKED on %s]" % blocked) if blocked else ""
        target = c.get("target") or "TBD"
        lines.append("  - [%s] %s%s" % (domain, c["item"], tag))
        lines.append("      done-means: %s" % c["done_means"])
        lines.append("      target: %s   next action: ______" % target)

    lines.append("")
    lines.append("STREAK CHECK:")
    for s in state.get("streaks", []):
        last = s.get("last_done") or "never"
        lines.append("  - %-18s current %d (best %d)  last: %s"
                     % (s["name"], s.get("current", 0), s.get("best", 0), last))

    lines.append("")
    lines.append("THE LINE:")
    below = state.get("the_line", {}).get("below_line", [])
    lines.append("  above: %s" % state.get("the_line", {}).get("above_line", "open scorecard items"))
    if below:
        lines.append("  below (logged, does NOT cut ahead):")
        for idea in below:
            lines.append("    · %s" % idea)
    else:
        lines.append("  below: (empty — no ideas parked)")

    lines.append("")
    lines.append("BOSS-RISK WARNING SIGNS TO CHECK:")
    for r in state.get("boss_risks", []):
        flag = "  <-- STANDING WATCH" if r.get("status") == "STANDING WATCH" else ""
        lines.append("  - %-18s signs: %s%s" % (r["name"], ", ".join(r["warning_signs"]), flag))

    lines.append("")
    lines.append("ONE HONEST OBSERVATION YOU DIDN'T ASK FOR: ______")
    return "\n".join(lines)


def check_line(state: dict) -> list:
    """Line Rule guard: warn if ideas are parked below the line while items are open above it."""
    warnings = []
    below = state.get("the_line", {}).get("below_line", [])
    opens = open_items(state)
    if below and opens:
        warnings.append(
            "LINE RULE: %d idea(s) parked below the line while %d scorecard item(s) are still open. "
            "Nothing below cuts ahead until something above closes." % (len(below), len(opens)))
    return warnings


def render_board(state: dict) -> str:
    m = state["meta"]
    parts = []
    parts.append("=" * 80)
    parts.append("LIFE SWEEP — %s & %s   (as of %s)" % (m["operator"], m["co_founder"], m["as_of"]))
    parts.append("=" * 80)
    parts.append(render_grades(state))
    parts.append("")

    parts.append("LIFE LEVELS (unlock in order):")
    for lv in state.get("life_levels", []):
        mark = "[x]" if lv.get("achieved") else "[ ]"
        parts.append("  %s %-3s %s" % (mark, lv["level"], lv["name"]))
    parts.append("")

    parts.append("LOCKED DECISIONS (not relitigated; new evidence may reopen, boredom may not):")
    for ld in state.get("locked_decisions", []):
        parts.append("  · %s" % ld)
    parts.append("")

    parts.append(render_sweep(state))

    for w in check_line(state):
        parts.append("")
        parts.append("!! " + w)
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Self-test — synthetic state, same convention as the swing modules
# --------------------------------------------------------------------------- #
def _synthetic_state() -> dict:
    """A deliberately broken state that exercises the enforced mechanics."""
    return {
        "meta": {
            "operator": "TEST", "co_founder": "TEST", "kids": [],
            "as_of": "2026-01-01",
            "season": {"label": "TEST season", "main_quest": "Execution"},
        },
        "domain_order": ["Wealth", "Execution", "Health"],
        "domains": {
            "Wealth":    {"grade": "A",  "movement": "→", "why": "strong", "graded": True},
            "Execution": {"grade": "A",  "movement": "↑", "why": "shipping", "graded": True},
            # Health failing -> must cap the A-average overall down to C.
            "Health":    {"grade": "F",  "movement": "↓", "why": "burnt out", "graded": True, "multiplier": True},
        },
        "scorecards": {"Execution": [
            {"item": "thing", "done_means": "done", "why_now": "now", "target": None,
             "status": "open", "blocked_on": None}]},
        "streaks": [{"name": "Sweep", "cadence": "weekly", "current": 0, "best": 0, "last_done": None}],
        "boss_risks": [{"name": "Burnout", "warning_signs": ["sleep debt"], "status": "STANDING WATCH"}],
        "life_levels": [{"level": "L1", "name": "burn covered", "achieved": True}],
        "locked_decisions": ["test locked"],
        "the_line": {"above_line": "open items", "below_line": ["a shiny idea"]},
    }


def _self_test() -> None:
    print("life_sweep self-test (synthetic state)")
    print("-" * 60)
    s = _synthetic_state()

    ov = compute_overall(s)
    assert ov.health_capped, "Health F must cap the overall"
    assert ov.grade == HEALTH_CAP_GRADE, "capped overall must be %s, got %s" % (HEALTH_CAP_GRADE, ov.grade)
    print("PASS  Health multiplier cap: two A's + Health F -> overall %s" % ov.grade)

    # Ungraded domains are excluded, not zeroed.
    s2 = _synthetic_state()
    s2["domains"]["Marriage"] = {"grade": None, "graded": False, "why": "no data"}
    s2["domain_order"].append("Marriage")
    ov2 = compute_overall(s2)
    assert "Marriage" in ov2.ungraded, "ungraded domain must be reported, not counted"
    print("PASS  Ungraded domain excluded & reported, not guessed into the number")

    # No-data-at-all -> undeclared, never a fabricated grade.
    empty = {"domains": {"X": {"grade": None, "graded": False}}, "domain_order": ["X"]}
    assert compute_overall(empty).grade == "N/A"
    print("PASS  Zero graded domains -> overall N/A (undeclared, not invented)")

    # Line Rule fires when an idea is parked while an item is open.
    warns = check_line(s)
    assert warns and "LINE RULE" in warns[0]
    print("PASS  Line Rule guard fires: idea parked below while item open above")

    # Binary points round-trip.
    assert points_to_grade(3.7) == "A-" and points_to_grade(0.0) == "F"
    print("PASS  Grade <-> points mapping")

    print("-" * 60)
    print("All self-tests passed.\n")


def main(argv: list) -> None:
    cmd = argv[1] if len(argv) > 1 else "selftest"
    if cmd == "selftest":
        _self_test()
        if os.path.exists(STATE_PATH):
            print(render_board(load_state()))
        else:
            print("(no life_state.json found — showing self-test only)")
        return

    if not os.path.exists(STATE_PATH):
        print("No life_state.json found at %s" % STATE_PATH)
        return
    state = load_state()
    if cmd == "board":
        print(render_board(state))
    elif cmd == "grades":
        print(render_grades(state))
    elif cmd == "sweep":
        print(render_sweep(state))
        for w in check_line(state):
            print("\n!! " + w)
    else:
        print("usage: python life_sweep.py [board|grades|sweep]")


if __name__ == "__main__":
    main(sys.argv)
