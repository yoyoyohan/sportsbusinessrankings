# Rating algorithm findings (from Drive workbooks)

Read-only analysis of all 27 local `.xlsm` copies. Drive is never written.

## How the spreadsheet engine works

Every sport workbook uses the same pattern:

1. **`Games`** — chronological results (Sheet1 in VBA)
2. **`Rank`** — live team ratings (Sheet2)
3. **`Calc`** — one-game calculator with Excel formulas (Sheet3)
4. **VBA** `HSRatingCalc` / `HSUpdater` — loops each new game, feeds it into Calc, reads the formula outputs, writes Ori/New back to Games, updates Rank

So the **math lives in Calc formulas**. VBA is the orchestrator, not a separate secret formula.

From Soccer VBA (`docs/vba_soccer_module1.txt`):

- Load team1/team2/scores/home into Calc
- Calc looks up current Off/Def/Games from Rank
- Read `C5/D5/C6/D6` as new Off/Def (or single rating for some sports)
- Write Ori/New/GD/Error onto the Games row
- If home: update home-edge accumulators `Q2/Q3/R2/R3`
- Add `delta` (usually **0.75**) to each team’s Games count on Rank

## Sport families (by Calc)

| Family | Count | Expected score idea | Rating state |
|--------|------:|---------------------|--------------|
| **Off/Def spread** | 15 | `Off − opp Def ± home edge` | Off + Def |
| **Single rating (fencing/swim)** | 4 | `Rating − opp Rating ± home` | one number |
| **Volleyball** | 2 | same, but expected capped at **25** | one number |
| **Bowling / gymnastics** | 3 | `Rating ± home` (no opponent subtract in G2) | one number |
| **Golf** | 1 | par-adjusted expected diff | one number |
| **Tennis** | 2 | line-score sheets; Calc not the same engine | 1S–2D lines |

### Off/Def sports (same Calc core as Soccer)

Boys/Girls Soccer, Football, Baseball, Softball, B/G Basketball, B/G Lacrosse, Field Hockey, Flag Football, B/G Hockey, B/G Wrestling.

### Confirmed Off/Def update (Calc)

For a home game (`H=1`):

```
exp1 = Off1 - Def2 + Q4      # Q4 = home edge
exp2 = Off2 - Def1 - R4      # R4 = away edge
exp1g = max(exp1, 0)
exp2g = max(exp2, 0)
K = score1 - exp1g           # team1 scoring surprise
L = score2 - exp2g           # team2 scoring surprise
w1 = min(Games1, 15)         # P1 = 15
w2 = min(Games2, 15)

NewOff1 = Off1 + K/w1   (with special cases when exp1 < 0)
NewDef1 = Def1 - L/w1   (mirror cases when exp2 < 0)
NewOff2 = Off2 + L/w2
NewDef2 = Def2 - K/w2
Rating  = Off + Def
```

Home edges `Q4` / `R4` are running averages from the **Q/R accumulator columns** (coach-confirmed; see below). Late-season Soccer: `Q4≈0.320325`.

Games weight: season start **2.75**; +**0.75** per game thereafter. New-team first Games weight follows same season-start convention once seeded.

## Season start & new teams (coach-confirmed)

### New season
- **Carry** Off and Def from the previous season.
- **Reset** Games weight to **2.75** for every team.

### Home edge (Q / R columns)
- Accumulators begin at **sum = 0**, **n = 1** → average `0/1 = 0`.
- After each home game, update the running sum/count; `Q4` / `R4` are the averages used in Calc.
- **Between seasons (current practice):** keep the same average, but **rescale the denominator to 100**.
  - Example (soccer): `9679.905 / 30219` → `32.0325 / 100` so home Off advantage stays **+0.320325**.
  - Purpose: allow gradual drift of HFA without a huge n that freezes the estimate, and without a tiny n that swings wildly.
- **Open idea (coach):** for a from-scratch 2015 rebuild, start at **0 with n = 100** (same average 0, but defended against early extremes). Worth testing when we replay history.

### New team mid-season
Invert the expected-score equations so the first game fits exactly given the opponent’s known Off/Def, the actual scores, and home/away edges (`Q4` / `R4`):

```
# Expected (from Calc):
score1 = Off1 - Def2 + Q4
score2 = Off2 - Def1 - R4

# Solve for the unknown side (new team):
Off1 = score1 + Def2 - Q4
Def1 = Off2 - R4 - score2
# (mirror if team 2 is the new team)
Off2 = score2 + Def1 + R4
Def2 = Off1 - score1 + Q4
```

Coach example (neutral, edges ≈ 0): opponent Off 5 / Def 2, new team loses 3–2 → new Off **4** (4−2=2), new Def **2** (5−2=3).

**UI rule:** adding a new team must be a **manual confirm** (not auto), so renames (e.g. Bishop Ahr → St. Thomas Aquinas) aren’t treated as brand-new schools.

## Tennis (coach-confirmed)

- One dual meet ≈ **10** regular-sport rating updates: **5 positions × 2 sets**.
- Each **position** has its **own rating**.
- System projects the score in **each set**; each set result updates that position’s rating (same family of update as other sports, applied per set/position).

## History & projections (product requirement)

- Goal: **rebuild all seasons** if possible; at minimum, **inject full game logs** and recompute ratings chronologically so the DB holds full history.
- Full history is required for **percentage projections**: share of past games where the projection was wrong by **at least as much as the listed spread**, then **÷ 2** (error can go either direction, but the underdog only covers when wrong in the specific direction).

## Validation status

| Test | Result |
|------|--------|
| Soccer Calc + end-season HFA on **last ~50 games** | Very close (errors often &lt; 0.01–0.04) |
| Full historical Soccer replay from 2015 with today’s Calc only | **Fails** without correct season Games reset, HFA rescale, seeds, and new-team handling — those rules are now documented |
| VBA pattern | Same `HSRatingCalc` / `HSUpdater` across Off/Def and single-rating sports |

**Conclusion:** Coach rules + Calc are enough to port Off/Def (and define tennis as 10 position-set updates). Next: Python engine + chronological replay from game logs; compare to Rank / Ori–New columns; try HFA `n=100` at 2015 origin if early extremes appear.

## Implementation (in repo)

| Module | Role |
|--------|------|
| `backend/rating_engine.py` | Off/Def, margin, volleyball cap, absolute/golf, tennis lines |
| `backend/recompute.py` | Replay game logs → `teams` + `sport_hfa` (+ tennis `line_matches`) |
| `POST /api/admin/recompute/{slug}` | Recompute one sport |
| `POST /api/admin/recompute-all` | Recompute every sport |
| Scheduled Drive refresh | Import then **recompute** so live rankings are native |

Engine modes (see `catalog.py`): `offdef`, `margin`, `margin_cap25`, `absolute`, `golf`, `lines`.

CLI: `python backend/recompute.py --all --sqlite`

## What “native algorithm on the site” means

1. Store games as source of truth in Supabase (full history)  
2. Keep team Off/Def (or Rating) + Games weight + HFA accumulators in DB  
3. On each new game (or full replay), run the Calc update in Python  
4. Derive spread % projections from historical projection-error distribution  
5. Drive import remains bootstrap / audit until replay matches  

## Files

- `data/_algo_catalog.json` — per-workbook sheet/Calc snapshot  
- `docs/vba_soccer_module1.txt` — extracted Soccer VBA  

