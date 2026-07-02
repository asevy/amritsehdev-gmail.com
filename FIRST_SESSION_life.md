# First session with Life Sweep — checklist

You have the operating manual (`LIFE_SWEEP.md`), the state
(`life_state.json`), and the enforcer (`life_sweep.py`). Goal of session 1:
confirm the mechanics hold, then fill in the two things only you can supply —
the missing grades and the target dates.

## 0. Confirm the machine runs
- [ ] `python life_sweep.py`          # self-test (Health cap, ungraded≠zero, Line Rule) + live board
- [ ] `python life_sweep.py grades`   # note: overall shows STATED A- vs the thin COMPUTED figure
- [ ] `python life_sweep.py sweep`    # the weekly-sweep skeleton

## 1. Set the project up as a Life Sweep game master
- [ ] Create a "Life Sweep" project; paste the **Role → Honesty rules** sections
      of `LIFE_SWEEP.md` as the project instructions.
- [ ] Point it at this repo so the game reads/writes `life_state.json`.

## 2. Fill in what only you know (then commit — the history is the record)
- [ ] First **monthly regrade**: give Health, Marriage, Kids, Family, Business,
      Craft, Adventure, Character a grade + a one-line why. Until then they stay
      ungraded on purpose — the engine will not guess them.
- [ ] Grade **Health honestly.** It's the multiplier; an F caps the whole board
      at C. This is the one grade the system protects you by *not* rounding up.
- [ ] Add **target dates** to the six Execution scorecard items (currently TBD).
- [ ] Declare your **streaks** (training, date nights, kid one-on-ones, sweeps)
      and their real current counts.

## 3. Good prompts to give the game master
- "Run the weekly sweep. Verify every 'closed' claim against the record before
   you credit it, and give me one honest observation I didn't ask for."
- "Monthly regrade. Move a grade only on completion, not on how good the plan
   is. Tell me which domain lagged on drift vs on a real dependency."
- "I've got a new idea: [X]. Log it below the line and tell me which open
   scorecard item has to close before it earns a look."

## 4. The safeguards (the sequence is the point)
- [ ] Grades pay on **completion**, never on commitment or planning quality.
- [ ] "Done means" is **binary** — no partial credit into a scorecard.
- [ ] **Locked decisions** are not relitigated; new evidence may reopen one,
      boredom may not.
- [ ] Nothing new **cuts the line** ahead of an open scorecard item.

## Honest reminder
The board is a focusing tool, not a scoreboard to win. When the score starts
costing the things it was built to protect — the kids' years, Munsa, your
health — that's the signal to put the game down, not to grind the grade. The
point of the game is the life.
