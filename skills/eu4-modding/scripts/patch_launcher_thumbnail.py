#!/usr/bin/env python3
"""Patch Paradox Launcher v2 thumbnailPath for a local EU4 mod.

Use only after the user explicitly approves editing launcher-v2.sqlite.
The script makes a timestamped database backup before writing.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import time
from pathlib import Path


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "local_mod"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--mod-dir", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument(
        "--display-name",
        help="Optional displayName filter if several launcher rows share a mod path.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip DB backup. Avoid this outside throwaway tests.",
    )
    args = parser.parse_args()

    db = args.db.resolve()
    mod_dir = args.mod_dir.resolve()
    image = args.image.resolve()
    if not db.exists():
        raise SystemExit(f"DB not found: {db}")
    if not mod_dir.exists():
        raise SystemExit(f"Mod directory not found: {mod_dir}")
    if not image.exists():
        raise SystemExit(f"Image not found: {image}")

    if not args.no_backup:
        backup = db.with_name(f"{db.name}.thumbnail-backup-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(db, backup)
        print(f"backup={backup}")

    con = sqlite3.connect(db)
    cur = con.cursor()
    query = """
        select id, displayName, dirPath
        from mods
        where lower(replace(dirPath, '/', '\\')) = lower(?)
    """
    params: list[str] = [str(mod_dir)]
    if args.display_name:
        query += " and displayName = ?"
        params.append(args.display_name)

    rows = list(cur.execute(query, params))
    if len(rows) != 1:
        raise SystemExit(f"Expected one matching mod row, found {len(rows)}: {rows}")

    mod_id, display_name, _dir_path = rows[0]
    cache_root = db.parent / ".launcher-cache" / f"local-mod-thumbnail-{safe_name(str(mod_id))}"
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_image = cache_root / image.name
    shutil.copy2(image, cache_image)

    cur.execute(
        """
        update mods
        set thumbnailPath = ?, thumbnailUrl = null, timeUpdated = ?
        where id = ?
        """,
        (str(cache_image), int(time.time()), mod_id),
    )
    con.commit()
    con.close()

    print(f"mod={display_name}")
    print(f"thumbnailPath={cache_image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
