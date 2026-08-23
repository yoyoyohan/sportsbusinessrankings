"""Import HSSpreadOffDef.numbers into SQLite."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from numbers_parser import Document

from db import DB_PATH, connect, get_meta, init_db, set_meta

DEFAULT_NUMBERS = Path(
    "/Users/yohandeshpande/Library/Mobile Documents/com~apple~Numbers/Documents/HSSpreadOffDef.numbers"
)

GROUP_SHEETS = [
    "GMC",
    "G4 State",
    "G3 State",
    "G2 State",
    "G1 State",
    "NPA State",
    "NPB State",
    "HV State",
]


def cell(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return int(round(v))
        return round(float(v), 6)
    if isinstance(v, str):
        s = v.strip()
        return s or None
    return v


def rows_of(doc: Document, name: str):
    return doc.sheets[name].tables[0].rows(values_only=True)


def import_numbers(source: Path, db_path: Path = DB_PATH) -> dict:
    print(f"Loading {source} …", flush=True)
    doc = Document(str(source))
    print("Loaded.", flush=True)

    conn = connect(db_path)
    init_db(conn)

    # wipe derived tables for a clean rebuild
    for table in (
        "teams",
        "games",
        "group_teams",
        "season_rows",
        "standings",
        "projections",
        "our_games",
        "last_week",
    ):
        conn.execute(f"DELETE FROM {table}")

    # Rank
    rank_rows = rows_of(doc, "Rank")
    as_of = cell(rank_rows[0][3])
    team_count = 0
    for r in rank_rows[1:]:
        team = cell(r[3])
        if not team or cell(r[4]) is None:
            continue
        conn.execute(
            """
            INSERT INTO teams(name, rank, rating, off, def, change, prev, games, n, last_game)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
              rank=excluded.rank, rating=excluded.rating, off=excluded.off, def=excluded.def,
              change=excluded.change, prev=excluded.prev, games=excluded.games, n=excluded.n,
              last_game=excluded.last_game
            """,
            (
                team,
                cell(r[2]),
                cell(r[4]),
                cell(r[5]),
                cell(r[6]),
                cell(r[1]),
                cell(r[0]),
                cell(r[8]),
                cell(r[9]),
                cell(r[7]),
            ),
        )
        team_count += 1

    # Games — full ori/new ratings for history
    games_rows = rows_of(doc, "Games")
    game_count = 0
    batch = []
    for r in games_rows[1:]:
        t1, s1, t2, s2 = cell(r[1]), cell(r[2]), cell(r[3]), cell(r[4])
        if not t1 or not t2 or s1 is None or s2 is None:
            continue
        try:
            s1i, s2i = int(s1), int(s2)
        except Exception:
            continue
        h = cell(r[5])
        batch.append(
            (
                cell(r[0]),
                t1,
                s1i,
                t2,
                s2i,
                1 if h == 1 else 0,
                cell(r[6]),
                cell(r[7]),
                cell(r[8]),
                cell(r[9]),
                cell(r[10]),
                cell(r[11]),
                cell(r[12]),
                cell(r[13]),
                cell(r[14]),
                cell(r[15]),
            )
        )
        if len(batch) >= 2000:
            conn.executemany(
                """
                INSERT INTO games(
                  date, team1, score1, team2, score2, home,
                  ori_off1, ori_def1, ori_off2, ori_def2,
                  new_off1, new_def1, new_off2, new_def2, gd, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            game_count += len(batch)
            batch.clear()
    if batch:
        conn.executemany(
            """
            INSERT INTO games(
              date, team1, score1, team2, score2, home,
              ori_off1, ori_def1, ori_off2, ori_def2,
              new_off1, new_def1, new_off2, new_def2, gd, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
        game_count += len(batch)

    # Groups
    for sheet in GROUP_SHEETS:
        rows = rows_of(doc, sheet)
        header = rows[0]
        rank = 0
        entries = []
        for i, v in enumerate(header):
            name = cell(v)
            if not name or not isinstance(name, str):
                continue
            off = cell(rows[1][i]) if len(rows) > 1 else None
            deff = cell(rows[2][i]) if len(rows) > 2 else None
            rating = None
            if off is not None and deff is not None:
                rating = round(float(off) + float(deff), 6)
            entries.append((name, off, deff, rating))
        entries.sort(key=lambda x: -(x[3] if x[3] is not None else -999))
        for i, (name, off, deff, rating) in enumerate(entries, 1):
            conn.execute(
                """
                INSERT INTO group_teams(group_key, team, rank, off, def, rating)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sheet, name, i, off, deff, rating),
            )

    # Sheet2 season
    for r in rows_of(doc, "Sheet2")[1:]:
        team = cell(r[0])
        if not team:
            continue
        conn.execute(
            """
            INSERT INTO season_rows(team, off, def, w, d, grp, pts, spread, odds, adjp, dist)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team) DO UPDATE SET
              off=excluded.off, def=excluded.def, w=excluded.w, d=excluded.d,
              grp=excluded.grp, pts=excluded.pts, spread=excluded.spread,
              odds=excluded.odds, adjp=excluded.adjp, dist=excluded.dist
            """,
            (
                team,
                cell(r[1]),
                cell(r[2]),
                cell(r[3]),
                cell(r[4]),
                cell(r[5]),
                cell(r[6]),
                cell(r[7]),
                cell(r[8]),
                cell(r[9]),
                cell(r[10]),
            ),
        )

    # Sheet3 standings
    for r in rows_of(doc, "Sheet3")[1:]:
        team = cell(r[0])
        if not team:
            continue
        conn.execute(
            """
            INSERT INTO standings(team, w, d, l, pts, off, def, gf, ga, gd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team) DO UPDATE SET
              w=excluded.w, d=excluded.d, l=excluded.l, pts=excluded.pts,
              off=excluded.off, def=excluded.def, gf=excluded.gf, ga=excluded.ga, gd=excluded.gd
            """,
            (
                team,
                cell(r[1]),
                cell(r[2]),
                cell(r[3]),
                cell(r[4]),
                cell(r[5]),
                cell(r[6]),
                cell(r[7]),
                cell(r[8]),
                cell(r[9]),
            ),
        )

    # Sheet4 projections
    for r in rows_of(doc, "Sheet4")[1:]:
        team = cell(r[0])
        if not team:
            continue
        conn.execute(
            """
            INSERT INTO projections(team, quality, pp, qual_diff, win_odds, exp_pp, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team) DO UPDATE SET
              quality=excluded.quality, pp=excluded.pp, qual_diff=excluded.qual_diff,
              win_odds=excluded.win_odds, exp_pp=excluded.exp_pp, notes=excluded.notes
            """,
            (
                team,
                cell(r[1]),
                cell(r[2]),
                cell(r[3]),
                cell(r[4]),
                cell(r[5]),
                cell(r[6]) if len(r) > 6 else None,
            ),
        )

    # OurGames
    for r in rows_of(doc, "OurGames")[1:]:
        game = cell(r[0])
        if not game:
            continue
        conn.execute(
            """
            INSERT INTO our_games(game, date, off, def, rating, running)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (game, cell(r[1]), cell(r[2]), cell(r[3]), cell(r[4]), cell(r[5])),
        )

    # Last Week
    for r in rows_of(doc, "Last Week")[1:]:
        team = cell(r[3])
        if not team or cell(r[4]) is None:
            continue
        conn.execute(
            """
            INSERT INTO last_week(team, rank, rating, off, def, change, prev, n, last_game)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team) DO UPDATE SET
              rank=excluded.rank, rating=excluded.rating, off=excluded.off, def=excluded.def,
              change=excluded.change, prev=excluded.prev, n=excluded.n, last_game=excluded.last_game
            """,
            (
                team,
                cell(r[2]),
                cell(r[4]),
                cell(r[5]),
                cell(r[6]),
                cell(r[1]),
                cell(r[0]),
                cell(r[9]),
                cell(r[7]),
            ),
        )

    set_meta(conn, "as_of", str(as_of or ""))
    set_meta(conn, "source", str(source))
    set_meta(conn, "imported_at", datetime.now().isoformat(timespec="seconds"))
    conn.commit()
    conn.close()

    summary = {
        "as_of": as_of,
        "source": str(source),
        "teams": team_count,
        "games": game_count,
    }
    print("Import complete:", summary, flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Import Numbers spreadsheet into ratings DB")
    parser.add_argument("--source", type=Path, default=DEFAULT_NUMBERS)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    if not args.source.exists():
        raise SystemExit(f"Source not found: {args.source}")
    import_numbers(args.source, args.db)


if __name__ == "__main__":
    main()
