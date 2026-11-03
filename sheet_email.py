"""Gmail without an App Password: phone/Code.gs (SCRIPT_VERSION 3+) copies order emails into the sheet's "Email" tab
every 30 minutes, and this module feeds them through the same parser as the IMAP path (gmail_sync.process)."""
import re
import sqlite3
from datetime import datetime

import db
import gmail_sync
import parsers
import phone_inbox
import rules

EMAIL_SCRIPT_VERSION = 3
PREFIX = "sheet:"   # emails.message_id of rows from the sheet; IMAP rows use the RFC Message-ID
MAX_PAGES = 50      # a=emails returns up to 100 rows a page; the tab keeps at most 1000
FWD_FROM = re.compile(r"^\s*(?:from|từ|tu)\s*:\s*(.+)$", re.I | re.M)


def script_version(conn: sqlite3.Connection) -> int:
    return int(db.get_setting(conn, "phone_script_version") or 0)


def available(conn: sqlite3.Connection) -> bool:
    return phone_inbox.connected(conn) and script_version(conn) >= EMAIL_SCRIPT_VERSION


def _sender(sender: str, subject: str, body: str) -> str:
    """A hand-forwarded email ("Fwd: …") comes from the forwarder; the shop's address is in the quoted header."""
    if parsers.platform_of(sender) != "other" or not re.match(r"^\s*(fwd?|tt)\s*:", subject or "", re.I):
        return sender
    for m in FWD_FROM.finditer("\n".join((body or "").splitlines()[:60])):
        if parsers.platform_of(m.group(1)) != "other":
            return m.group(1).strip()
    return sender


def _day(stamp) -> str:
    try:
        return datetime.fromisoformat(str(stamp)[:19]).isoformat(timespec="seconds")
    except ValueError:
        return datetime.now().isoformat(timespec="seconds")


def pull(conn: sqlite3.Connection, code: str) -> dict:
    """Fetch every row after the stored cursor, then apply them oldest first like gmail_sync.sync."""
    cursor = db.get_setting(conn, "sheet_email_cursor")
    rows, reply = [], {}
    for _ in range(MAX_PAGES):  # all pages before any is applied: a cancellation must not be read before its order
        reply = phone_inbox._get(code, "emails", since=cursor)
        rows += reply.get("rows", [])
        cursor = reply.get("next") or cursor
        if not reply.get("more"):
            break
    known = {r[0] for r in conn.execute("SELECT message_id FROM emails WHERE message_id LIKE ?", (PREFIX + "%",))}
    fresh, seen = [], set()
    for r in rows:
        mid = PREFIX + str(r.get("id") or "").strip()
        if mid == PREFIX or mid in known or mid in seen:
            continue
        seen.add(mid)
        fresh.append((_day(r.get("date")), mid, r))

    counts: dict = {"found": len(rows), "new": len(fresh)}
    compiled = rules.load(conn)
    for stamp, mid, r in sorted(fresh, key=lambda x: (x[0], x[1])):
        subject, body = str(r.get("subject") or ""), str(r.get("body") or "")
        sender = _sender(str(r.get("from") or ""), subject, body)
        received = stamp[:10]
        # An order email without an order number is keyed by a hash of its message id; the RFC one matches IMAP's.
        status, tx_id = gmail_sync.process(conn, compiled, str(r.get("mid") or "").strip() or mid, received, sender,
                                           subject, body)
        conn.execute("INSERT OR REPLACE INTO emails(message_id, received, sender, subject, body, status, "
                     "transaction_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (mid, received, sender, subject, body if status != "skipped" else "", status, tx_id))
        counts[status] = counts.get(status, 0) + 1
    db.set_setting(conn, "sheet_email_cursor", cursor)
    db.set_setting(conn, "sheet_email_scanned", str(reply.get("scanned") or ""))
    db.set_setting(conn, "sheet_email_last_pull", datetime.now().strftime("%Y-%m-%d %H:%M"))
    db.set_setting(conn, "sheet_email_error", "")
    return counts


def status(conn: sqlite3.Connection) -> dict:
    """For /api/info: the status line under "Đọc Gmail qua Google Sheet"."""
    count, last = conn.execute("SELECT COUNT(*), MAX(received) FROM emails WHERE message_id LIKE ?",
                               (PREFIX + "%",)).fetchone()
    return {"sheet_email_required": EMAIL_SCRIPT_VERSION, "sheet_email_available": available(conn),
            "sheet_email_count": count, "sheet_email_last_date": last or "",
            "sheet_email_last_pull": db.get_setting(conn, "sheet_email_last_pull"),
            "sheet_email_scanned": db.get_setting(conn, "sheet_email_scanned"),
            "sheet_email_error": db.get_setting(conn, "sheet_email_error")}


def forget(conn: sqlite3.Connection) -> None:
    """Another sheet's ids mean nothing here; stored emails stay so their transactions keep their source."""
    for key in ("sheet_email_cursor", "sheet_email_scanned", "sheet_email_last_pull", "sheet_email_error"):
        db.set_setting(conn, key, "")
