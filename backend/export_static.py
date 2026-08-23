"""Build a static copy of the site for Netlify (no live API)."""

from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from catalog import SPORTS, sport_by_slug  # noqa: E402
from db import DB_PATH, ROOT as DB_ROOT, connect, init_db  # noqa: E402

STATIC = DB_ROOT / "static"
DIST = DB_ROOT / "dist"


def row_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


def public_sport(row) -> dict:
    return {
        "slug": row["slug"],
        "name": row["name"],
        "as_of": row["as_of"],
    }


def combo(off, deff):
    if off is None and deff is None:
        return None
    if deff is None:
        return round(float(off), 6) if off is not None else None
    if off is None:
        return round(float(deff), 6)
    return round(float(off) + float(deff), 6)


def history_for(name: str, games: list) -> tuple[list, list]:
    history = []
    for g in games:
        if g["team1"] == name:
            opponent, gf, ga = g["team2"], g["score1"], g["score2"]
            home = bool(g["home"])
            ori_off, ori_def = g["ori_off1"], g["ori_def1"]
            new_off, new_def = g["new_off1"], g["new_def1"]
        else:
            opponent, gf, ga = g["team1"], g["score2"], g["score1"]
            home = not bool(g["home"])
            ori_off, ori_def = g["ori_off2"], g["ori_def2"]
            new_off, new_def = g["new_off2"], g["new_def2"]
        ori_rating = combo(ori_off, ori_def)
        new_rating = combo(new_off, new_def)
        delta = None
        if ori_rating is not None and new_rating is not None:
            delta = round(new_rating - ori_rating, 6)
        gf = gf or 0
        ga = ga or 0
        result = "W" if gf > ga else ("L" if gf < ga else "D")
        history.append(
            {
                "date": g["date"],
                "opponent": opponent,
                "gf": gf,
                "ga": ga,
                "home": home,
                "result": result,
                "ori_rating": ori_rating,
                "new_rating": new_rating,
                "rating_delta": delta,
            }
        )
    recent = history[-80:] if len(history) > 80 else history
    chart = [
        {"date": h["date"], "rating": h["new_rating"], "delta": h["rating_delta"]}
        for h in history
        if h["new_rating"] is not None and h["date"]
    ][-120:]
    return list(reversed(recent)), chart


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":"), default=str), encoding="utf-8")


def copy_frontend() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    assets = DIST / "assets"
    shutil.copytree(STATIC / "css", assets / "css")
    (assets / "js").mkdir()
    for name in ("home.js", "sport.js", "team.js", "util.js"):
        shutil.copy(STATIC / "js" / name, assets / "js" / name)
    for name in ("index.html", "sport.html", "team.html"):
        html = (STATIC / name).read_text(encoding="utf-8")
        html = html.replace('\n        <a href="/admin">Update</a>', "")
        html = html.replace('\n        <a href="/admin" class="current">Update</a>', "")
        (DIST / name).write_text(html, encoding="utf-8")
    (DIST / "_redirects").write_text(
        "/s/*/team  /team.html  200\n/s/*       /sport.html  200\n",
        encoding="utf-8",
    )
    (DIST / "netlify.toml").write_text(
        "\n".join(
            [
                "[build]",
                '  publish = "."',
                "",
                "[[redirects]]",
                '  from = "/s/*/team"',
                '  to = "/team.html"',
                "  status = 200",
                "",
                "[[redirects]]",
                '  from = "/s/*"',
                '  to = "/sport.html"',
                "  status = 200",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (DIST / "404.html").write_text(
        "<!DOCTYPE html><meta charset='utf-8'><title>Not found</title>"
        "<p>Page not found. <a href='/'>NJ HS Ratings</a></p>\n",
        encoding="utf-8",
    )


def export() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing database: {DB_PATH}. Import workbooks first.")
    copy_frontend()
    conn = connect()
    init_db(conn)

    sports_rows = [row_dict(r) for r in conn.execute("SELECT * FROM sports ORDER BY name").fetchall()]
    sports_out = []
    for s in sports_rows:
        spec = sport_by_slug(s["slug"]) or {}
        ranked = conn.execute(
            "SELECT COUNT(*) AS c FROM teams WHERE sport_id = ? AND rank IS NOT NULL",
            (s["id"],),
        ).fetchone()["c"]
        sports_out.append(
            {
                **public_sport(s),
                "ranked": ranked,
                "group": spec.get("group"),
                "kind": spec.get("kind"),
            }
        )
    write_json(
        DIST / "data" / "status.json",
        {
            "public": True,
            "sports": sports_out,
            "catalog": [{"slug": s["slug"], "name": s["name"], "group": s["group"]} for s in SPORTS],
        },
    )

    for s in sports_rows:
        slug = s["slug"]
        spec = sport_by_slug(slug) or {}
        kind = spec.get("kind")
        sport = public_sport(s)
        print(f"Exporting {sport['name']}…", flush=True)

        teams = [
            row_dict(r)
            for r in conn.execute(
                """
                SELECT name, rank, rating, off, def, change, prev, games, n, last_game
                FROM teams
                WHERE sport_id = ? AND rank IS NOT NULL
                ORDER BY rank ASC, name ASC
                """,
                (s["id"],),
            ).fetchall()
        ]
        write_json(
            DIST / "data" / slug / "rankings.json",
            {"sport": sport, "kind": kind, "total": len(teams), "teams": teams},
        )

        games_recent = [
            row_dict(r)
            for r in conn.execute(
                """
                SELECT date, team1, score1, team2, score2, home
                FROM games
                WHERE sport_id = ?
                ORDER BY date DESC, id DESC
                LIMIT 250
                """,
                (s["id"],),
            ).fetchall()
        ]
        write_json(
            DIST / "data" / slug / "results.json",
            {"sport": sport, "games": games_recent},
        )

        ranked_names = {t["name"] for t in teams}
        by_team: dict[str, list] = defaultdict(list)
        game_rows = conn.execute(
            """
            SELECT date, team1, score1, team2, score2, home,
                   ori_off1, ori_def1, ori_off2, ori_def2,
                   new_off1, new_def1, new_off2, new_def2
            FROM games
            WHERE sport_id = ?
            ORDER BY date ASC, id ASC
            """,
            (s["id"],),
        ).fetchall()
        for g in game_rows:
            gd = row_dict(g)
            if gd["team1"] in ranked_names:
                by_team[gd["team1"]].append(gd)
            if gd["team2"] in ranked_names:
                by_team[gd["team2"]].append(gd)

        by_name = {}
        for t in teams:
            recent, chart = history_for(t["name"], by_team.get(t["name"], []))
            by_name[t["name"]] = {"team": t, "history": recent, "chart": chart}
        write_json(
            DIST / "data" / slug / "teams.json",
            {"sport": sport, "kind": kind, "byName": by_name},
        )

    conn.close()
    print(f"Wrote {DIST}")


if __name__ == "__main__":
    export()
