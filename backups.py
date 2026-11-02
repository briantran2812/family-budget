"""Copy budget.db aside before a new app version migrates it, so an update can be rolled back (docs/DEPLOY.md F)."""
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

import db

KEEP = 10
VERSION_KEY = "db_version"  # the app version that last opened this database


def stored_version(path: Path) -> str | None:
    """Version recorded in the database; for databases from before 1.4.0, the last 'Có gì mới' seen, else 'unknown'."""
    with closing(sqlite3.connect(path)) as c:
        try:
            rows = dict(c.execute("SELECT key, value FROM settings WHERE key IN (?, 'seen_version')", (VERSION_KEY,)))
        except sqlite3.OperationalError:  # no settings table yet
            return "unknown"
    return rows.get(VERSION_KEY) or rows.get("seen_version") or "unknown"


def backup_if_upgraded(version: str, now: datetime | None = None) -> Path | None:
    """Back up the database when it was last opened by another version. Returns the backup's path, or None."""
    path = db.DB_PATH
    if not path.exists() or path.stat().st_size == 0:
        return None  # first start: nothing to protect
    old = stored_version(path)
    if old == version:
        return None
    folder = path.parent / "backups"
    folder.mkdir(exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M")
    target = folder / f"budget-{old}-{stamp}.db"
    n = 2
    while target.exists():
        target = folder / f"budget-{old}-{stamp}-{n}.db"
        n += 1
    # sqlite's backup API, not a file copy: the copy holds the last committed state even after a crash.
    with closing(sqlite3.connect(path)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    for stale in sorted(folder.glob("budget-*.db"), key=lambda p: (p.stat().st_mtime, p.name))[:-KEEP]:
        stale.unlink()
    return target


def open_database(version: str) -> None:
    """App start: back up if the version changed, migrate (db.init), then record the version."""
    try:
        saved = backup_if_upgraded(version)
        if saved:
            print(f"backed up the database before upgrading to {version}: {saved}", file=sys.stderr)
    except (OSError, sqlite3.Error) as e:  # a full disk must not keep the app from opening; the log says why
        print(f"database backup before upgrade failed: {e}", file=sys.stderr)
    db.init()
    with db.connect() as c:
        db.set_setting(c, VERSION_KEY, version)
