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

Home edges `Q4/R4` are **running averages** updated after each home game (not fixed constants). Late-season Soccer values were about `Q4≈0.32`, `R4≈-0.05`.

Games weight starts near **2–2.75** for new teams and increases by **0.75** per game.

## Validation status

| Test | Result |
|------|--------|
| Soccer Calc formulas + end-season HFA on **last ~50 games** | Very close (errors often &lt; 0.01–0.04); ~60% exact with approximate Games weights |
| Full historical Soccer replay from 2015 with today’s Calc | **Fails** — early rows don’t match (likely evolving HFA, seed ratings, and/or formula changes over years) |
| VBA present in Football, Volleyball, Bowling, Golf | Same `HSRatingCalc` / `HSUpdater` pattern; rating-only sports write one rating instead of Off/Def |

**Conclusion:** We understand the **current** engine well enough to port Off/Def sports. We should **not** expect bit-identical rebuild of a decade of history without his seed/HFA starting values and any old formula versions.

## What “native algorithm on the site” means

1. Store games as source of truth in Supabase  
2. Keep team Off/Def (or Rating) + Games weight in DB  
3. On each new game, run the Calc update (Python port of the family formulas)  
4. Optionally keep Drive import as a bootstrap / audit against Rank  

## Still need from coach (optional but helpful)

- Initial Games weight / seed ratings for a new season  
- Whether older seasons used different Calc  
- Tennis: confirm line-rating rules separately  

## Files

- `data/_algo_catalog.json` — per-workbook sheet/Calc snapshot  
- `docs/vba_soccer_module1.txt` — extracted Soccer VBA  
