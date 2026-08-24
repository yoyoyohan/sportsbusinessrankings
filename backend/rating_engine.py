"""Native Off/Def rating engine (port of spreadsheet Calc + VBA HSUpdater).

Drive workbooks remain read-only bootstrap/audit; this module owns forward math.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


GAMES_CAP = 15.0
GAMES_DELTA = 0.75
GAMES_SEASON_START = 2.75
HFA_SEASON_N = 100.0
HFA_REBUILD_N = 100.0  # coach preference for from-scratch replay


@dataclass
class TeamState:
    off: float
    deff: float | None = 0.0
    games: float = GAMES_SEASON_START
    # Tennis position ratings (1S,2S,3S,1D,2D); overall rating is their sum
    lines: dict[str, float] | None = None

    @property
    def rating(self) -> float:
        if self.lines:
            return sum(self.lines.values())
        if self.deff is None:
            return self.off
        return self.off + self.deff


@dataclass
class HfaState:
    """Q/R running averages used as home/away edges (Calc Q4/R4)."""

    q_sum: float = 0.0
    q_n: float = HFA_REBUILD_N
    r_sum: float = 0.0
    r_n: float = HFA_REBUILD_N

    @property
    def q4(self) -> float:
        return self.q_sum / self.q_n if self.q_n else 0.0

    @property
    def r4(self) -> float:
        return self.r_sum / self.r_n if self.r_n else 0.0

    def rescale_to_n(self, n: float = HFA_SEASON_N) -> None:
        """Between seasons: keep averages, set denominator to n."""
        q_avg, r_avg = self.q4, self.r4
        self.q_n = n
        self.r_n = n
        self.q_sum = q_avg * n
        self.r_sum = r_avg * n


@dataclass
class GameResult:
    ori_off1: float
    ori_def1: float
    ori_off2: float
    ori_def2: float
    new_off1: float
    new_def1: float
    new_off2: float
    new_def2: float
    games1: float
    games2: float
    exp1: float
    exp2: float
    gd: float
    error: float
    seeded1: bool = False
    seeded2: bool = False


def _w(games: float, cap: float = GAMES_CAP) -> float:
    g = float(games)
    return g if g < cap else cap


def _floor0(x: float) -> float:
    return x if x > 0 else 0.0


def _off_delta(exp: float, score: float, surprise: float, games: float) -> float:
    """N2 / O2: Off bump for a team."""
    w = _w(games)
    if exp < 0:
        if score > 0:
            return (score - exp) / w
        return surprise / w
    return surprise / w


def _def_delta_vs_opp_exp(opp_exp: float, opp_score: float, opp_surprise: float, my_games: float) -> float:
    """N3 / O3: Def bump (already signed as in Calc)."""
    w = _w(my_games)
    if opp_exp < 0:
        if opp_score > 0:
            return -((opp_score - opp_exp) / w)
        return -(opp_surprise / w)
    return -(opp_surprise / w)


def expected_scores(
    off1: float,
    def1: float,
    off2: float,
    def2: float,
    home: bool,
    hfa: HfaState,
) -> tuple[float, float]:
    q = hfa.q4 if home else 0.0
    r = hfa.r4 if home else 0.0
    return off1 - def2 + q, off2 - def1 - r


def seed_new_team(
    score_new: float,
    score_opp: float,
    opp_off: float,
    opp_def: float,
    *,
    new_is_team1: bool,
    home: bool,
    hfa: HfaState,
) -> tuple[float, float]:
    """Invert expected-score equations so the game fits the known opponent."""
    q = hfa.q4 if home else 0.0
    r = hfa.r4 if home else 0.0
    if new_is_team1:
        # score1 = Off1 - Def2 + q  → Off1 = score1 + Def2 - q
        # score2 = Off2 - Def1 - r  → Def1 = Off2 - r - score2
        return score_new + opp_def - q, opp_off - r - score_opp
    # new is team2: score2 = Off2 - Def1 - r; score1 = Off1 - Def2 + q
    return score_new + opp_def + r, opp_off + q - score_opp


def seed_both_new(score1: float, score2: float, home: bool, hfa: HfaState) -> tuple[TeamState, TeamState]:
    """Underdetermined; use Off = score (± edge), Def = 0 so expected ≈ actual."""
    q = hfa.q4 if home else 0.0
    r = hfa.r4 if home else 0.0
    return (
        TeamState(off=score1 - q, deff=0.0, games=GAMES_SEASON_START),
        TeamState(off=score2 + r, deff=0.0, games=GAMES_SEASON_START),
    )


def apply_offdef_game(
    t1: TeamState,
    t2: TeamState,
    score1: int | float,
    score2: int | float,
    home: bool,
    hfa: HfaState,
    *,
    games_delta: float = GAMES_DELTA,
    update_hfa: bool = True,
) -> GameResult:
    """One game through Calc + HFA accumulator update + Games += delta."""
    s1, s2 = float(score1), float(score2)
    exp1, exp2 = expected_scores(t1.off, t1.deff, t2.off, t2.deff, home, hfa)
    k = s1 - _floor0(exp1)
    l = s2 - _floor0(exp2)

    n2 = _off_delta(exp1, s1, k, t1.games)
    o2 = _off_delta(exp2, s2, l, t2.games)
    n3 = _def_delta_vs_opp_exp(exp2, s2, l, t1.games)
    o3 = _def_delta_vs_opp_exp(exp1, s1, k, t2.games)

    new_off1 = t1.off + n2
    new_def1 = t1.deff + n3
    new_off2 = t2.off + o2
    new_def2 = t2.deff + o3

    pred_margin = _floor0(exp1) - _floor0(exp2)
    gd = s1 - s2
    err = abs(gd - pred_margin)

    if update_hfa and home:
        # K5/L5 use no-HFA expected (G5/H5)
        g5 = t1.off - t2.deff
        h5 = t2.off - t1.deff
        k5 = s1 - _floor0(g5)
        l5 = s2 - _floor0(h5)
        hfa.q_sum += k5
        hfa.q_n += 1
        hfa.r_sum -= l5
        hfa.r_n += 1

    ori = (t1.off, t1.deff, t2.off, t2.deff)
    t1.off, t1.deff = new_off1, new_def1
    t2.off, t2.deff = new_off2, new_def2
    t1.games += games_delta
    t2.games += games_delta

    return GameResult(
        ori_off1=ori[0],
        ori_def1=ori[1],
        ori_off2=ori[2],
        ori_def2=ori[3],
        new_off1=new_off1,
        new_def1=new_def1,
        new_off2=new_off2,
        new_def2=new_def2,
        games1=t1.games,
        games2=t2.games,
        exp1=exp1,
        exp2=exp2,
        gd=gd,
        error=err,
    )


def apply_margin_game(
    t1: TeamState,
    t2: TeamState,
    score1: int | float,
    score2: int | float,
    home: bool,
    hfa: HfaState,
    *,
    games_delta: float = GAMES_DELTA,
    cap: float | None = None,
    update_hfa: bool = True,
) -> GameResult:
    """Single-rating margin sports (fencing/swim) and volleyball (cap=25)."""
    s1, s2 = float(score1), float(score2)
    q = hfa.q4 if home else 0.0
    exp = t1.off - t2.off + q
    if cap is not None and exp > cap:
        exp = cap
    actual = s1 - s2
    m = actual - exp
    w1, w2 = _w(t1.games), _w(t2.games)
    n2, o2 = m / w1, -m / w2
    new1, new2 = t1.off + n2, t2.off + o2
    if update_hfa and home:
        # fencing G5 ≈ 13.5 + 0.5*(r1-r2); volleyball different — use margin residual
        hfa.q_sum += m
        hfa.q_n += 1
    ori1, ori2 = t1.off, t2.off
    t1.off, t2.off = new1, new2
    t1.games += games_delta
    t2.games += games_delta
    return GameResult(
        ori_off1=ori1,
        ori_def1=None,
        ori_off2=ori2,
        ori_def2=None,
        new_off1=new1,
        new_def1=None,
        new_off2=new2,
        new_def2=None,
        games1=t1.games,
        games2=t2.games,
        exp1=exp,
        exp2=0.0,
        gd=actual,
        error=abs(m),
    )


def apply_absolute_game(
    t1: TeamState,
    t2: TeamState,
    score1: int | float,
    score2: int | float,
    home: bool,
    hfa: HfaState,
    *,
    games_delta: float = GAMES_DELTA,
    par: float = 0.0,
    holes: float = 36.0,
    update_hfa: bool = True,
) -> GameResult:
    """Bowling / gymnastics (rating = expected score) and golf (par + rating)."""
    s1, s2 = float(score1), float(score2)
    if holes and holes != 36:
        s1 = s1 / (holes / 36.0)
        s2 = s2 / (holes / 36.0)
    q = hfa.q4 if home else 0.0
    exp1 = par + t1.off + q
    exp2 = par + t2.off
    k = s1 - _floor0(exp1)
    l = s2 - _floor0(exp2)
    n2 = _off_delta(exp1, s1, k, t1.games)
    o2 = _off_delta(exp2, s2, l, t2.games)
    new1, new2 = t1.off + n2, t2.off + o2
    if update_hfa and home:
        hfa.q_sum += s1 - _floor0(par + t1.off)
        hfa.q_n += 1
    ori1, ori2 = t1.off, t2.off
    t1.off, t2.off = new1, new2
    t1.games += games_delta
    t2.games += games_delta
    pred = _floor0(exp1) - _floor0(exp2)
    gd = s1 - s2
    return GameResult(
        ori_off1=ori1,
        ori_def1=None,
        ori_off2=ori2,
        ori_def2=None,
        new_off1=new1,
        new_def1=None,
        new_off2=new2,
        new_def2=None,
        games1=t1.games,
        games2=t2.games,
        exp1=exp1,
        exp2=exp2,
        gd=gd,
        error=abs(gd - pred),
    )


LINE_POSITIONS = ("1S", "2S", "3S", "1D", "2D")


def apply_line_position(
    r1: float,
    r2: float,
    score1: float,
    score2: float,
    home: bool,
    hfa: HfaState,
    games1: float,
    games2: float,
) -> tuple[float, float, float]:
    """One tennis position update (margin vs rating gap). Returns (new1, new2, error)."""
    q = hfa.q4 if home else 0.0
    exp = r1 - r2 + q
    # Calc clamps projected edge for some displays; update uses raw margin error
    actual = float(score1) - float(score2)
    m = actual - exp
    w1, w2 = _w(games1), _w(games2)
    return r1 + m / w1, r2 - m / w2, abs(m)


def season_key(date: str | None, group: str) -> str:
    """Stable season label for rollover (Games reset + HFA rescale)."""
    if not date or len(date) < 7:
        return "unknown"
    y, m = int(date[:4]), int(date[5:7])
    group = (group or "").lower()
    if group == "winter":
        return str(y if m >= 8 else y - 1)
    # Fall / Spring / default: calendar year of the game date
    return str(y)


@dataclass
class EngineState:
    teams: dict[str, TeamState] = field(default_factory=dict)  # key: lowercase name
    canonical: dict[str, str] = field(default_factory=dict)  # lower -> display name
    hfa: HfaState = field(default_factory=HfaState)
    current_season: str | None = None
    auto_seed_new: bool = True
    engine: str = "offdef"
    games_delta: float = GAMES_DELTA

    def _key(self, name: str) -> str:
        return name.strip().lower()

    def display_name(self, name: str) -> str:
        return self.canonical.get(self._key(name), name.strip())

    def get(self, name: str) -> TeamState | None:
        return self.teams.get(self._key(name))

    def on_season_change(self, new_season: str) -> None:
        if self.current_season is None:
            self.current_season = new_season
            return
        if new_season == self.current_season:
            return
        for t in self.teams.values():
            t.games = GAMES_SEASON_START
        self.hfa.rescale_to_n(HFA_SEASON_N)
        self.current_season = new_season

    def _register(self, name: str, st: TeamState) -> TeamState:
        key = self._key(name)
        self.teams[key] = st
        self.canonical.setdefault(key, name.strip())
        return st

    def _blank_team(self) -> TeamState:
        if self.engine == "lines":
            return TeamState(off=0.0, deff=None, games=GAMES_SEASON_START, lines={p: 0.0 for p in LINE_POSITIONS})
        if self.engine == "offdef":
            return TeamState(off=0.0, deff=0.0, games=GAMES_SEASON_START)
        return TeamState(off=0.0, deff=None, games=GAMES_SEASON_START)

    def _seed_pair(
        self,
        team1: str,
        team2: str,
        score1: float,
        score2: float,
        home: bool,
        *,
        par: float = 0.0,
    ) -> tuple[TeamState, TeamState, bool, bool]:
        has1 = self.get(team1) is not None
        has2 = self.get(team2) is not None
        seeded1 = seeded2 = False
        q = self.hfa.q4 if home else 0.0

        if self.engine == "offdef":
            if not has1 and not has2:
                t1, t2 = seed_both_new(score1, score2, home, self.hfa)
                self._register(team1, t1)
                self._register(team2, t2)
                return t1, t2, True, True
            if not has1:
                t2 = self.get(team2)
                assert t2 is not None
                off, deff = seed_new_team(score1, score2, t2.off, t2.deff or 0.0, new_is_team1=True, home=home, hfa=self.hfa)
                t1 = self._register(team1, TeamState(off, deff, GAMES_SEASON_START))
                return t1, t2, True, False
            if not has2:
                t1 = self.get(team1)
                assert t1 is not None
                off, deff = seed_new_team(score2, score1, t1.off, t1.deff or 0.0, new_is_team1=False, home=home, hfa=self.hfa)
                t2 = self._register(team2, TeamState(off, deff, GAMES_SEASON_START))
                return t1, t2, False, True
            return self.get(team1), self.get(team2), False, False  # type: ignore

        # Single-rating families
        if not has1 and not has2:
            t1 = self._register(team1, TeamState(off=score1 - par - q, deff=None, games=GAMES_SEASON_START))
            t2 = self._register(team2, TeamState(off=score2 - par, deff=None, games=GAMES_SEASON_START))
            if self.engine in ("margin", "margin_cap25"):
                # margin seed: rating gap = score gap
                margin = score1 - score2
                t1.off = margin / 2
                t2.off = -margin / 2
            return t1, t2, True, True
        if not has1:
            t2 = self.get(team2)
            assert t2 is not None
            if self.engine in ("margin", "margin_cap25"):
                off = (score1 - score2) + t2.off - q
            else:
                off = score1 - par - q
            t1 = self._register(team1, TeamState(off=off, deff=None, games=GAMES_SEASON_START))
            return t1, t2, True, False
        if not has2:
            t1 = self.get(team1)
            assert t1 is not None
            if self.engine in ("margin", "margin_cap25"):
                off = t1.off - (score1 - score2) + q
            else:
                off = score2 - par
            t2 = self._register(team2, TeamState(off=off, deff=None, games=GAMES_SEASON_START))
            return t1, t2, False, True
        t1, t2 = self.get(team1), self.get(team2)
        assert t1 and t2
        for name, st in ((team1, t1), (team2, t2)):
            key = self._key(name)
            if name.strip() and name.strip()[0].isupper():
                self.canonical[key] = name.strip()
        return t1, t2, False, False

    def process_game(
        self,
        date: str | None,
        team1: str,
        score1: int | float,
        team2: str,
        score2: int | float,
        home: bool,
        group: str = "Fall",
        *,
        course_par: float | None = None,
        holes: float = 36.0,
    ) -> GameResult:
        self.on_season_change(season_key(date, group))
        home_b = bool(home)
        par = float(course_par or 0.0)
        t1, t2, seeded1, seeded2 = self._seed_pair(
            team1, team2, float(score1), float(score2), home_b, par=par
        )

        if self.engine == "offdef":
            result = apply_offdef_game(
                t1, t2, score1, score2, home_b, self.hfa, games_delta=self.games_delta
            )
        elif self.engine == "margin":
            result = apply_margin_game(
                t1, t2, score1, score2, home_b, self.hfa, games_delta=self.games_delta
            )
        elif self.engine == "margin_cap25":
            result = apply_margin_game(
                t1, t2, score1, score2, home_b, self.hfa, games_delta=self.games_delta, cap=25.0
            )
        elif self.engine in ("absolute", "golf"):
            result = apply_absolute_game(
                t1,
                t2,
                score1,
                score2,
                home_b,
                self.hfa,
                games_delta=self.games_delta,
                par=par if self.engine == "golf" else 0.0,
                holes=holes if self.engine == "golf" else 36.0,
            )
        else:
            raise ValueError(f"Unsupported engine in process_game: {self.engine}")

        result.seeded1 = seeded1
        result.seeded2 = seeded2
        return result

    def process_tennis_dual(
        self,
        date: str | None,
        home_team: str,
        away_team: str,
        home: bool,
        scores: dict[str, tuple[float, float]],
        group: str = "Spring",
    ) -> dict:
        """Update five position ratings; Games += delta once per dual."""
        self.on_season_change(season_key(date, group))
        home_b = bool(home)

        def ensure_lines(name: str) -> TeamState:
            st = self.get(name)
            if st is None:
                st = self._blank_team()
                self._register(name, st)
            if not st.lines:
                st.lines = {p: 0.0 for p in LINE_POSITIONS}
            return st

        t1 = ensure_lines(home_team)
        t2 = ensure_lines(away_team)
        errors = []
        for pos in LINE_POSITIONS:
            if pos not in scores:
                continue
            s1, s2 = scores[pos]
            if s1 is None or s2 is None:
                continue
            r1 = t1.lines[pos]
            r2 = t2.lines[pos]
            n1, n2, err = apply_line_position(r1, r2, s1, s2, home_b, self.hfa, t1.games, t2.games)
            t1.lines[pos] = n1
            t2.lines[pos] = n2
            errors.append(err)
            if home_b:
                self.hfa.q_sum += (s1 - s2) - (r1 - r2)
                self.hfa.q_n += 1
        t1.off = t1.rating
        t2.off = t2.rating
        t1.games += self.games_delta
        t2.games += self.games_delta
        return {"error": sum(errors) / len(errors) if errors else 0.0, "positions": len(errors)}


def ranked_rows(
    teams: dict[str, TeamState],
    *,
    canonical: dict[str, str] | None = None,
    active_only: bool = True,
    games_delta: float = GAMES_DELTA,
) -> list[dict]:
    rows = []
    for key, t in teams.items():
        if active_only and t.games <= GAMES_SEASON_START + 1e-9:
            continue
        name = (canonical or {}).get(key, key)
        deff = t.deff
        rows.append(
            {
                "name": name,
                "off": t.off if deff is not None else t.rating,
                "def": deff,
                "rating": t.rating,
                "games": t.games,
                "n": (t.games - GAMES_SEASON_START) / games_delta if games_delta else None,
                "last_game": None,
                "lines": dict(t.lines) if t.lines else None,
            }
        )
    rows.sort(key=lambda r: (-(r["rating"] if r["rating"] is not None else -1e9), r["name"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def validate_single_steps(
    games: Iterable[dict],
    hfa: HfaState | None = None,
) -> dict:
    """Compare engine New* to spreadsheet New* using each row's Ori* as inputs."""
    hfa = hfa or HfaState(q_sum=0.320325 * 30219, q_n=30219, r_sum=-0.04712 * 30217, r_n=30217)
    checked = 0
    abs_err = 0.0
    max_err = 0.0
    mismatches = []
    for g in games:
        try:
            ori = (
                float(g["ori_off1"]),
                float(g["ori_def1"]),
                float(g["ori_off2"]),
                float(g["ori_def2"]),
            )
            expected_new = (
                float(g["new_off1"]),
                float(g["new_def1"]),
                float(g["new_off2"]),
                float(g["new_def2"]),
            )
        except (TypeError, ValueError, KeyError):
            continue
        games1 = float(g.get("games1") or GAMES_CAP)
        games2 = float(g.get("games2") or GAMES_CAP)
        t1 = TeamState(ori[0], ori[1], games1)
        t2 = TeamState(ori[2], ori[3], games2)
        hfa_snap = HfaState(hfa.q_sum, hfa.q_n, hfa.r_sum, hfa.r_n)
        got = apply_offdef_game(
            t1, t2, g["score1"], g["score2"], bool(g.get("home")), hfa_snap, update_hfa=False
        )
        pred = (got.new_off1, got.new_def1, got.new_off2, got.new_def2)
        errs = [abs(a - b) for a, b in zip(pred, expected_new)]
        e = max(errs)
        abs_err += sum(errs) / 4
        max_err = max(max_err, e)
        checked += 1
        if e > 0.05:
            mismatches.append(
                {
                    "date": g.get("date"),
                    "team1": g.get("team1"),
                    "team2": g.get("team2"),
                    "max_err": round(e, 6),
                    "pred": [round(x, 6) for x in pred],
                    "sheet": [round(x, 6) for x in expected_new],
                }
            )
    return {
        "checked": checked,
        "mean_abs_err": round(abs_err / checked, 6) if checked else None,
        "max_abs_err": round(max_err, 6) if checked else None,
        "mismatch_over_0_05": len(mismatches),
        "sample_mismatches": mismatches[:10],
    }
