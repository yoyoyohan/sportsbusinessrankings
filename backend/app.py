"""Multi-sport ratings API. Drive access is GET-only."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from catalog import DRIVE_FOLDER_URL, SPORTS, sport_by_slug
from db import ROOT, connect, get_meta, get_sport, init_db
from drive_sync import refresh_sport_file
from import_workbook import import_all, import_sport

NO_STORE = {"Cache-Control": "no-store, max-age=0"}

app = FastAPI(title="NJ HS Spread Ratings", version="0.3.0")
STATIC = ROOT / "static"


def row_dict(row) -> dict[str, Any]:
    data = {k: row[k] for k in row.keys()}
    data.pop("source_path", None)
    return data


def require_admin(request: Request) -> None:
    token = os.environ.get("ADMIN_TOKEN")
    if not token:
        return
    got = request.headers.get("x-admin-token") or request.query_params.get("token")
    if got != token:
        raise HTTPException(401, "Admin token required")


def open_db():
    """Open DB or raise a clear HTTP error (never crash the process)."""
    try:
        conn = connect()
        init_db(conn)
        return conn
    except Exception as exc:
        raise HTTPException(503, f"Database unavailable: {exc}") from exc


def sport_or_404(conn, slug: str):
    row = get_sport(conn, slug)
    if not row:
        raise HTTPException(404, f"Unknown sport: {slug}")
    return row


@app.on_event("startup")
def startup():
    # Never block or crash boot — free Render restarts if this fails.
    try:
        conn = connect()
        init_db(conn)
        conn.close()
    except Exception as exc:
        print(f"startup db warn: {exc}", flush=True)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/status")
def status():
    conn = open_db()
    try:
        sports = [
            row_dict(r)
            for r in conn.execute(
                "SELECT id, slug, name, as_of, imported_at, file_mtime, watch FROM sports ORDER BY name"
            ).fetchall()
        ]
        team_counts = {
            r["sport_id"]: r["c"]
            for r in conn.execute("SELECT sport_id, COUNT(*) AS c FROM teams GROUP BY sport_id").fetchall()
        }
        ranked_counts = {
            r["sport_id"]: r["c"]
            for r in conn.execute(
                "SELECT sport_id, COUNT(*) AS c FROM teams WHERE rank IS NOT NULL GROUP BY sport_id"
            ).fetchall()
        }
        game_counts = {
            r["sport_id"]: r["c"]
            for r in conn.execute("SELECT sport_id, COUNT(*) AS c FROM games GROUP BY sport_id").fetchall()
        }
        for s in sports:
            sid = s["id"]
            s["teams"] = team_counts.get(sid, 0)
            s["ranked"] = ranked_counts.get(sid, 0)
            s["games"] = game_counts.get(sid, 0)
            spec = sport_by_slug(s["slug"])
            if spec:
                s["group"] = spec["group"]
                s["kind"] = spec["kind"]
        return {
            "drive_folder": DRIVE_FOLDER_URL,
            "drive_write": False,
            "last_refresh_at": get_meta(conn, "last_refresh_at"),
            "last_refresh_ok": get_meta(conn, "last_refresh_ok"),
            "sports": sports,
            "catalog": [{"slug": s["slug"], "name": s["name"], "group": s["group"]} for s in SPORTS],
        }
    finally:
        conn.close()


@app.post("/api/admin/refresh-all")
def admin_refresh_all(request: Request):
    """Re-download every catalog file from Drive (GET only), then import."""
    require_admin(request)
    try:
        from scheduled_refresh import run as scheduled_run

        return scheduled_run()
    except Exception as exc:
        raise HTTPException(500, f"Refresh failed: {exc}") from exc


@app.get("/api/sports")
def list_sports():
    return status()


@app.get("/api/sports/{slug}/rankings")
def rankings(
    slug: str,
    q: str | None = None,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_matches: int | None = None,
    ranked_only: bool = True,
    sort: str = "rank",
    dir: str = "asc",
    limit: int = Query(600, ge=1, le=2000),
):
    allowed = {"rank", "rating", "off", "def", "change", "n", "name", "last_game", "games"}
    if sort not in allowed:
        sort = "rank"
    direction = "DESC" if dir.lower() == "desc" else "ASC"
    order = f'CASE WHEN "{sort}" IS NULL THEN 1 ELSE 0 END, "{sort}" {direction}, name ASC'

    conn = open_db()
    try:
        sport = sport_or_404(conn, slug)
        clauses = ["sport_id = ?"]
        params: list[Any] = [sport["id"]]
        if ranked_only:
            clauses.append("rank IS NOT NULL")
        if q:
            clauses.append("name LIKE ?")
            params.append(f"%{q}%")
        if min_rating is not None:
            clauses.append("rating >= ?")
            params.append(min_rating)
        if max_rating is not None:
            clauses.append("rating <= ?")
            params.append(max_rating)
        if min_matches is not None:
            clauses.append("COALESCE(n,0) >= ?")
            params.append(min_matches)
        where = "WHERE " + " AND ".join(clauses)
        rows = [
            row_dict(r)
            for r in conn.execute(
                f"SELECT * FROM teams {where} ORDER BY {order} LIMIT ?",
                [*params, limit],
            ).fetchall()
        ]
        total = conn.execute(f"SELECT COUNT(*) AS c FROM teams {where}", params).fetchone()["c"]
        spec = sport_by_slug(slug) or {}
        return {
            "sport": row_dict(sport),
            "kind": spec.get("kind"),
            "total": total,
            "teams": rows,
        }
    finally:
        conn.close()


@app.get("/api/sports/{slug}/results")
def results(slug: str, q: str | None = None, limit: int = Query(250, ge=1, le=1000)):
    conn = open_db()
    try:
        sport = sport_or_404(conn, slug)
        clauses = ["sport_id = ?"]
        params: list[Any] = [sport["id"]]
        if q:
            clauses.append("(team1 LIKE ? OR team2 LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        where = "WHERE " + " AND ".join(clauses)
        rows = conn.execute(
            f"""
            SELECT date, team1, score1, team2, score2, home
            FROM games {where}
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return {"sport": row_dict(sport), "games": [row_dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/sports/{slug}/teams/{name}")
def team_detail(slug: str, name: str):
    conn = open_db()
    try:
        sport = sport_or_404(conn, slug)
        team = conn.execute(
            "SELECT * FROM teams WHERE sport_id = ? AND name = ?",
            (sport["id"], name),
        ).fetchone()
        if not team:
            team = conn.execute(
                "SELECT * FROM teams WHERE sport_id = ? AND LOWER(name) = LOWER(?)",
                (sport["id"], name),
            ).fetchone()
        if not team:
            raise HTTPException(404, f"Team not found: {name}")
        name = team["name"]
        games = conn.execute(
            """
            SELECT * FROM games
            WHERE sport_id = ? AND (team1 = ? OR team2 = ?)
            ORDER BY date ASC, id ASC
            """,
            (sport["id"], name, name),
        ).fetchall()

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

            def combo(off, deff):
                if off is None and deff is None:
                    return None
                if deff is None:
                    return round(float(off), 6) if off is not None else None
                if off is None:
                    return round(float(deff), 6)
                return round(float(off) + float(deff), 6)

            ori_rating = combo(ori_off, ori_def)
            new_rating = combo(new_off, new_def)
            delta = None
            if ori_rating is not None and new_rating is not None:
                delta = round(new_rating - ori_rating, 6)
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
        spec = sport_by_slug(slug) or {}
        return {
            "sport": row_dict(sport),
            "kind": spec.get("kind"),
            "team": row_dict(team),
            "history": list(reversed(recent)),
            "history_all_count": len(history),
            "chart": chart,
        }
    finally:
        conn.close()


@app.post("/api/admin/import/{slug}")
def admin_import_one(slug: str, request: Request):
    require_admin(request)
    if not sport_by_slug(slug):
        raise HTTPException(404, slug)
    try:
        return {"ok": True, **import_sport(slug, include_games=True)}
    except FileNotFoundError as exc:
        raise HTTPException(404, f"Local copy missing: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"Import failed: {exc}") from exc


@app.post("/api/admin/import-all")
def admin_import_all(request: Request):
    require_admin(request)
    try:
        return {"ok": True, "results": import_all(include_games=True)}
    except Exception as exc:
        raise HTTPException(500, f"Import failed: {exc}") from exc


@app.post("/api/admin/refresh/{slug}")
def admin_refresh_one(slug: str, request: Request):
    """Download a fresh copy from Drive (GET only), then import locally."""
    require_admin(request)
    if not sport_by_slug(slug):
        raise HTTPException(404, slug)
    try:
        path = refresh_sport_file(slug)
        summary = import_sport(slug, include_games=True)
        return {"ok": True, "downloaded": str(path), **summary, "drive_write": False}
    except Exception as exc:
        raise HTTPException(500, f"Refresh failed: {exc}") from exc


def page(name: str) -> FileResponse:
    return FileResponse(STATIC / name, headers=NO_STORE)


if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC)), name="assets")
    app.mount("/css", StaticFiles(directory=str(STATIC / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(STATIC / "js")), name="js")


@app.get("/")
def index():
    return page("index.html")


@app.get("/s/{slug}")
def sport_page(slug: str):
    return page("sport.html")


@app.get("/s/{slug}/team")
def team_page(slug: str):
    return page("team.html")


@app.get("/admin")
def admin_page():
    return page("admin.html")
