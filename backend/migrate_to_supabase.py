"""Copy local SQLite ratings into Supabase Postgres. Drive is never written."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from db import (  # noqa: E402
    DB_PATH,
    connect_postgres,
    connect_sqlite,
    get_database_url,
    init_db,
)

TABLES = [
    ("sports", ["id", "slug", "name", "source_path", "as_of", "imported_at", "file_mtime", "watch"]),
    ("meta", ["key", "value"]),
    ("teams", ["sport_id", "name", "rank", "rating", "off", "def", "change", "prev", "games", "n", "last_game"]),
    (
        "games",
        [
            "id",
            "sport_id",
            "date",
            "team1",
            "score1",
            "team2",
            "score2",
            "home",
            "ori_off1",
            "ori_def1",
            "ori_off2",
            "ori_def2",
            "new_off1",
            "new_def1",
            "new_off2",
            "new_def2",
            "gd",
            "error",
        ],
    ),
    ("group_teams", ["sport_id", "group_key", "team", "rank", "off", "def", "rating"]),
    ("season_rows", ["sport_id", "team", "off", "def", "w", "d", "grp", "pts", "spread", "odds", "adjp", "dist"]),
    ("standings", ["sport_id", "team", "w", "d", "l", "pts", "off", "def", "gf", "ga", "gd"]),
    ("projections", ["sport_id", "team", "quality", "pp", "qual_diff", "win_odds", "exp_pp", "notes"]),
    ("our_games", ["id", "sport_id", "game", "date", "off", "def", "rating", "running"]),
    ("last_week", ["sport_id", "team", "rank", "rating", "off", "def", "change", "prev", "n", "last_game"]),
]


def copy_table(src, dest, table: str, cols: list[str]) -> int:
    exists = src.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    if not exists:
        print(f"  {table}: skipped (missing in SQLite)")
        return 0
    quoted = ", ".join(f'"{c}"' for c in cols)
    rows = src.execute(f"SELECT {quoted} FROM {table}").fetchall()
    if not rows:
        print(f"  {table}: 0")
        return 0
    placeholders = ", ".join("?" for _ in cols)
    colsql = ", ".join(f'"{c}"' for c in cols)
    sql = f'INSERT INTO {table} ({colsql}) VALUES ({placeholders})'
    batch: list[tuple] = []
    count = 0
    for r in rows:
        batch.append(tuple(r[c] for c in cols))
        if len(batch) >= 1000:
            dest.executemany(sql, batch)
            count += len(batch)
            batch.clear()
    if batch:
        dest.executemany(sql, batch)
        count += len(batch)
    print(f"  {table}: {count}")
    return count


def reset_identity(dest, table: str) -> None:
    dest.execute(
        f"""
        SELECT setval(
            pg_get_serial_sequence('public.{table}', 'id'),
            GREATEST(COALESCE((SELECT MAX(id) FROM {table}), 1), 1)
        )
        """
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload local ratings.db to Supabase.")
    parser.add_argument("--url", help="Postgres URI (otherwise DATABASE_URL)")
    parser.add_argument("--yes", action="store_true", help="Replace existing Supabase data")
    args = parser.parse_args()
    url = args.url or get_database_url()
    if not url:
        raise SystemExit(
            "Set DATABASE_URL in .env or pass --url 'postgresql://...'"
        )
    if not DB_PATH.exists():
        raise SystemExit(f"Missing {DB_PATH}. Import workbooks first.")
    if not args.yes:
        raise SystemExit("This replaces ratings data in Supabase. Re-run with --yes to continue.")

    print("Connecting to Supabase…")
    dest = connect_postgres(url)
    init_db(dest)
    src = connect_sqlite(DB_PATH)
    init_db(src)

    print("Clearing existing Postgres tables…")
    dest.execute(
        """
        TRUNCATE TABLE
          last_week, our_games, projections, standings, season_rows,
          group_teams, games, teams, meta, sports
        RESTART IDENTITY CASCADE
        """
    )

    print("Copying…")
    for table, cols in TABLES:
        copy_table(src, dest, table, cols)

    for table in ("sports", "games", "our_games"):
        try:
            reset_identity(dest, table)
        except Exception as exc:
            print(f"  sequence {table}: {exc}")

    dest.commit()
    sports = dest.execute("SELECT COUNT(*) AS c FROM sports").fetchone()["c"]
    teams = dest.execute("SELECT COUNT(*) AS c FROM teams").fetchone()["c"]
    games = dest.execute("SELECT COUNT(*) AS c FROM games").fetchone()["c"]
    src.close()
    dest.close()
    print(f"Done. sports={sports} teams={teams} games={games}")


if __name__ == "__main__":
    main()
