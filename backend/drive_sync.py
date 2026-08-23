"""Read-only Google Drive downloads. Never upload, edit, or share-write."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from catalog import SPORTS
from db import SOURCES_DIR

# GET only. Do not add any Drive upload/update calls.


def _curl_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if "proxy" in key.lower():
            env.pop(key, None)
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
    return env


def download_file(drive_id: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.unlink(missing_ok=True)

    urls = [
        "https://drive.usercontent.google.com/download?"
        f"id={drive_id}&export=download&confirm=t",
        f"https://drive.google.com/uc?export=download&confirm=t&id={drive_id}",
    ]

    last_err = "Drive download failed"
    for url in urls:
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "-L",
                "--fail",
                "--retry",
                "2",
                "--noproxy",
                "*",
                "-A",
                "Mozilla/5.0",
                "-o",
                str(tmp),
                url,
            ],
            capture_output=True,
            text=True,
            env=_curl_env(),
        )
        if result.returncode == 0 and tmp.exists() and tmp.stat().st_size > 1000:
            header = tmp.read_bytes()[:4]
            if header[:2] == b"PK":
                tmp.replace(dest)
                return
            last_err = "Drive returned a web page instead of the spreadsheet"
        else:
            last_err = (result.stderr or result.stdout or "Drive download failed").strip()
        tmp.unlink(missing_ok=True)

    raise RuntimeError(last_err)


def refresh_sport_file(slug: str) -> Path:
    spec = next((s for s in SPORTS if s["slug"] == slug), None)
    if not spec:
        raise KeyError(slug)
    dest = SOURCES_DIR / spec["file"]
    download_file(spec["drive_id"], dest)
    return dest


def refresh_all_files() -> list[dict]:
    out = []
    for spec in SPORTS:
        dest = SOURCES_DIR / spec["file"]
        download_file(spec["drive_id"], dest)
        out.append({"slug": spec["slug"], "file": spec["file"], "bytes": dest.stat().st_size})
    return out
