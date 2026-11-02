"""The in-app bell: a short history of things worth a look (budget alerts, new entries, a new version, failed syncs)."""
import json
import sqlite3

KEEP = 200


def add(conn: sqlite3.Connection, kind: str, icon: str, title: str, body: str = "", link: dict | None = None,
        dedupe: str | None = None) -> None:
    """`dedupe` makes the call idempotent (a version announcement, one push error per day)."""
    conn.execute("INSERT OR IGNORE INTO notifications(kind, icon, title, body, link, dedupe) VALUES (?, ?, ?, ?, ?, ?)",
                 (kind, icon, title, body, json.dumps(link, ensure_ascii=False) if link else None, dedupe))
    conn.execute("DELETE FROM notifications WHERE id NOT IN (SELECT id FROM notifications ORDER BY id DESC LIMIT ?)",
                 (KEEP,))


def listing(conn: sqlite3.Connection, limit: int = 50) -> dict:
    rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE read_at IS NULL").fetchone()[0]
    return {"unread": unread, "items": [{**dict(r), "link": json.loads(r["link"]) if r["link"] else None} for r in rows]}


def mark_read(conn: sqlite3.Connection, nid: int | None = None) -> None:
    sql = "UPDATE notifications SET read_at = datetime('now', 'localtime') WHERE read_at IS NULL"
    conn.execute(sql + (" AND id = ?" if nid else ""), (nid,) if nid else ())
