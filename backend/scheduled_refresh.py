"""Download Drive copies (GET only) and import into the configured database.

Used by the Render cron job so rankings refresh without a human click.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from catalog import SPORTS  # noqa: E402
from db import connect, ensure_schema_extras, get_database_url, init_db, set_meta  # noqa: E402
from drive_sync import refresh_sport_file  # noqa: E402
from import_workbook import import_sport  # noqa: E402


def run(*, recompute: bool = False) -> dict:
    """Download Drive copies and import Rank + Games into the database.

    By default rankings come from the spreadsheet Rank sheet (coach's truth).
    Pass recompute=True only for engine testing — that rebuilds from game logs
    and will not match Excel.
    """
    if not get_database_url():
        print("WARNING: DATABASE_URL is not set; importing into local SQLite.", flush=True)
    else:
        # Ensure Postgres extras exist before the first sport (avoids aborted transactions)
        try:
            conn = connect()
            init_db(conn)
            ensure_schema_extras(conn)
            conn.close()
        except Exception as exc:
            print(f"schema bootstrap failed: {exc}", flush=True)
            traceback.print_exc()

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"scheduled refresh start {started}", flush=True)

    results = []
    errors = []
    for spec in SPORTS:
        slug = spec["slug"]
        print(f"  refresh {slug} …", flush=True)
        try:
            path = refresh_sport_file(slug)
            summary = import_sport(slug, include_games=True)
            print(f"    imported teams={summary.get('teams')} games={summary.get('games')}", flush=True)
            entry = {
                "slug": slug,
                "ok": True,
                "downloaded": str(path),
                **summary,
                "rankings_source": "drive_rank",
            }
            if recompute:
                from recompute import recompute_sport

                recomputed = recompute_sport(slug)
                entry["recompute"] = {
                    "teams": recomputed.get("teams"),
                    "engine": recomputed.get("engine"),
                    "top5": recomputed.get("top5"),
                }
                entry["rankings_source"] = "native_engine"
                print(
                    f"    recomputed engine={recomputed.get('engine')} teams={recomputed.get('teams')}",
                    flush=True,
                )
            results.append(entry)
        except Exception as exc:
            errors.append({"slug": slug, "error": str(exc)})
            print(f"    FAIL {exc}", flush=True)
            traceback.print_exc()

    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ok = len(errors) == 0
    try:
        conn = connect()
        init_db(conn)
        set_meta(conn, "last_refresh_at", finished)
        set_meta(conn, "last_refresh_ok", "1" if ok else "0")
        set_meta(conn, "last_refresh_errors", str(len(errors)))
        set_meta(conn, "rankings_source", "native_engine" if recompute else "drive_rank")
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"meta write failed: {exc}", flush=True)

    print(
        f"scheduled refresh done ok={ok} sports={len(results)} errors={len(errors)} at {finished}",
        flush=True,
    )
    return {
        "ok": ok,
        "started": started,
        "finished": finished,
        "results": results,
        "errors": errors,
        "drive_write": False,
    }


if __name__ == "__main__":
    summary = run()
    # Fail the GitHub Action if any sport failed (partial success still updates meta)
    if summary["errors"]:
        print(
            f"ERROR: {len(summary['errors'])} sport(s) failed: "
            + ", ".join(e["slug"] for e in summary["errors"]),
            flush=True,
        )
        sys.exit(1)
    if not summary["results"]:
        sys.exit(1)
    sys.exit(0)
