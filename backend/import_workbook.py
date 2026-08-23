"""Import Rank + Games from local .xlsm copies. Workbooks are never written."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from catalog import SPORTS, sport_by_slug
from db import SOURCES_DIR, connect, init_db, clear_sport_data

GROUP_SHEETS = {
    "GMC",
    "State",
    "HV State",
    "G4 State",
    "G3 State",
    "G2 State",
    "G1 State",
    "NPA State",
    "NPB State",
}


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
        if not s or s.startswith("#"):
            return None
        return s
    return v


def _header_map(row) -> dict[str, int]:
    out = {}
    for i, v in enumerate(row):
        if v is None:
            continue
        key = str(v).strip().lower()
        if key and key not in out:
            out[key] = i
    return out


def _iter_sheet(path: Path, name: str, max_col: int = 20):
    wb = load_workbook(path, read_only=True, data_only=True, keep_vba=False)
    if name not in wb.sheetnames:
        wb.close()
        return None, []
    ws = wb[name]
    rows = ws.iter_rows(max_col=max_col, values_only=True)
    return wb, rows


def import_sport(slug: str, include_games: bool = True) -> dict:
    spec = sport_by_slug(slug)
    if not spec:
        raise KeyError(slug)
    path = SOURCES_DIR / spec["file"]
    if not path.exists():
        raise FileNotFoundError(path)

    conn = connect()
    init_db(conn)
    row = conn.execute("SELECT id FROM sports WHERE slug = ?", (slug,)).fetchone()
    if row:
        sport_id = row["id"]
        conn.execute(
            "UPDATE sports SET name = ?, source_path = ? WHERE id = ?",
            (spec["name"], str(path), sport_id),
        )
    else:
        row = conn.execute(
            "INSERT INTO sports(slug, name, source_path, watch) VALUES (?, ?, ?, 1) RETURNING id",
            (slug, spec["name"], str(path)),
        ).fetchone()
        sport_id = row["id"]
    clear_sport_data(conn, sport_id)

    as_of, team_count = _import_rank(conn, path, sport_id)
    game_count = 0
    if include_games:
        game_count = _import_games(conn, path, sport_id)
    _import_groups(conn, path, sport_id)

    imported_at = datetime.now().isoformat(timespec="seconds")
    mtime = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE sports
        SET as_of = ?, imported_at = ?, file_mtime = ?, source_path = ?
        WHERE id = ?
        """,
        (as_of, imported_at, mtime, str(path), sport_id),
    )
    conn.commit()
    conn.close()
    return {
        "slug": slug,
        "name": spec["name"],
        "as_of": as_of,
        "teams": team_count,
        "games": game_count,
        "file": spec["file"],
    }


def _import_rank(conn, path: Path, sport_id: int) -> tuple[str | None, int]:
    wb, rows = _iter_sheet(path, "Rank")
    if rows is None:
        return None, 0
    header = next(rows, None)
    if not header:
        wb.close()
        return None, 0
    hmap = _header_map(header)
    as_of = cell(header[3]) if len(header) > 3 else None
    off_i = hmap.get("offrating")
    def_i = hmap.get("defrating")
    date_i = hmap.get("date")
    games_i = hmap.get("games")
    n_i = hmap.get("n")
    count = 0
    batch = []
    for r in rows:
        team = cell(r[3]) if len(r) > 3 else None
        rating = cell(r[4]) if len(r) > 4 else None
        if not team or not isinstance(team, str) or rating is None:
            continue
        try:
            float(rating)
        except (TypeError, ValueError):
            continue
        off = cell(r[off_i]) if off_i is not None and off_i < len(r) else None
        deff = cell(r[def_i]) if def_i is not None and def_i < len(r) else None
        last_game = cell(r[date_i]) if date_i is not None and date_i < len(r) else None
        games = cell(r[games_i]) if games_i is not None and games_i < len(r) else None
        n = cell(r[n_i]) if n_i is not None and n_i < len(r) else None
        batch.append(
            (
                sport_id,
                team,
                cell(r[2]),
                rating,
                off,
                deff,
                cell(r[1]),
                cell(r[0]),
                games,
                n,
                last_game,
            )
        )
        count += 1
        if len(batch) >= 500:
            conn.executemany(
                """
                INSERT INTO teams(sport_id, name, rank, rating, off, def, change, prev, games, n, last_game)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sport_id, name) DO UPDATE SET
                  rank=excluded.rank, rating=excluded.rating, off=excluded.off, def=excluded.def,
                  change=excluded.change, prev=excluded.prev, games=excluded.games, n=excluded.n,
                  last_game=excluded.last_game
                """,
                batch,
            )
            batch.clear()
    if batch:
        conn.executemany(
            """
            INSERT INTO teams(sport_id, name, rank, rating, off, def, change, prev, games, n, last_game)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sport_id, name) DO UPDATE SET
              rank=excluded.rank, rating=excluded.rating, off=excluded.off, def=excluded.def,
              change=excluded.change, prev=excluded.prev, games=excluded.games, n=excluded.n,
              last_game=excluded.last_game
            """,
            batch,
        )
    wb.close()
    return str(as_of) if as_of else None, count


def _import_games(conn, path: Path, sport_id: int) -> int:
    wb, rows = _iter_sheet(path, "Games", max_col=16)
    if rows is None:
        return 0
    header = next(rows, None)
    if not header:
        wb.close()
        return 0
    hmap = _header_map(header)
    # Tennis (and similar) ledgers are line-score sheets, not team-vs-team ratings rows.
    if "home team" in hmap or "match date" in hmap:
        wb.close()
        return 0
    offdef = "orioff1" in hmap or "newoff1" in hmap
    count = 0
    batch = []
    for r in rows:
        if not r or len(r) < 5:
            continue
        t1, s1, t2, s2 = cell(r[1]), cell(r[2]), cell(r[3]), cell(r[4])
        if not t1 or not t2 or s1 is None or s2 is None:
            continue
        try:
            s1i, s2i = int(float(s1)), int(float(s2))
        except (TypeError, ValueError):
            continue
        h = cell(r[5]) if len(r) > 5 else None
        if offdef:
            ori_off1, ori_def1 = cell(r[6]), cell(r[7])
            ori_off2, ori_def2 = cell(r[8]), cell(r[9])
            new_off1, new_def1 = cell(r[10]), cell(r[11])
            new_off2, new_def2 = cell(r[12]), cell(r[13])
            gd = cell(r[14]) if len(r) > 14 else None
            err = cell(r[15]) if len(r) > 15 else None
        else:
            # Ori1, Ori2, New1, New2 live in the overall-rating columns
            ori_off1, ori_def1 = cell(r[6]) if len(r) > 6 else None, None
            ori_off2, ori_def2 = cell(r[7]) if len(r) > 7 else None, None
            new_off1, new_def1 = cell(r[8]) if len(r) > 8 else None, None
            new_off2, new_def2 = cell(r[9]) if len(r) > 9 else None, None
            gd = cell(r[10]) if len(r) > 10 else None
            err = cell(r[11]) if len(r) > 11 else None
        batch.append(
            (
                sport_id,
                cell(r[0]),
                t1,
                s1i,
                t2,
                s2i,
                1 if h == 1 else 0,
                ori_off1,
                ori_def1,
                ori_off2,
                ori_def2,
                new_off1,
                new_def1,
                new_off2,
                new_def2,
                gd,
                err,
            )
        )
        if len(batch) >= 2000:
            conn.executemany(
                """
                INSERT INTO games(
                  sport_id, date, team1, score1, team2, score2, home,
                  ori_off1, ori_def1, ori_off2, ori_def2,
                  new_off1, new_def1, new_off2, new_def2, gd, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            count += len(batch)
            batch.clear()
    if batch:
        conn.executemany(
            """
            INSERT INTO games(
              sport_id, date, team1, score1, team2, score2, home,
              ori_off1, ori_def1, ori_off2, ori_def2,
              new_off1, new_def1, new_off2, new_def2, gd, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
        count += len(batch)
    wb.close()
    return count


def _import_groups(conn, path: Path, sport_id: int) -> None:
    wb = load_workbook(path, read_only=True, data_only=True, keep_vba=False)
    for sheet in wb.sheetnames:
        if sheet not in GROUP_SHEETS:
            continue
        ws = wb[sheet]
        rows = list(ws.iter_rows(max_row=3, max_col=80, values_only=True))
        if len(rows) < 3:
            continue
        header, offs, defs = rows[0], rows[1], rows[2]
        entries = []
        for i, v in enumerate(header):
            name = cell(v)
            if not name or not isinstance(name, str):
                continue
            off = cell(offs[i]) if i < len(offs) else None
            deff = cell(defs[i]) if i < len(defs) else None
            rating = None
            if off is not None and deff is not None:
                try:
                    rating = round(float(off) + float(deff), 6)
                except (TypeError, ValueError):
                    rating = None
            elif off is not None:
                try:
                    rating = float(off)
                except (TypeError, ValueError):
                    rating = None
            entries.append((name, off, deff, rating))
        entries.sort(key=lambda x: -(x[3] if x[3] is not None else -9999))
        for i, (name, off, deff, rating) in enumerate(entries, 1):
            conn.execute(
                """
                INSERT INTO group_teams(sport_id, group_key, team, rank, off, def, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sport_id, group_key, team) DO UPDATE SET
                  rank=excluded.rank, off=excluded.off, def=excluded.def, rating=excluded.rating
                """,
                (sport_id, sheet, name, i, off, deff, rating),
            )
    wb.close()


def import_all(include_games: bool = True) -> list[dict]:
    results = []
    for spec in SPORTS:
        print(f"Import {spec['slug']} …", flush=True)
        results.append(import_sport(spec["slug"], include_games=include_games))
        print(" ", results[-1], flush=True)
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import local spreadsheet copies (read-only).")
    parser.add_argument("--slug")
    parser.add_argument("--no-games", action="store_true")
    args = parser.parse_args()
    if args.slug:
        print(import_sport(args.slug, include_games=not args.no_games))
    else:
        import_all(include_games=not args.no_games)
