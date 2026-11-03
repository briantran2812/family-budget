"""Thống kê sử dụng: how this app itself is used, kept 60 days on this Mac and added to the Sheet mirror ("Tổng hợp",
groups "Hoạt động" and "Lỗi") while the setting share_usage is on. Never keystrokes, other apps or the screen."""
import re
import sqlite3
from datetime import datetime

import db

KEEP_DAYS = 60
ERRORS_SENT = 10
WHERE_LABEL = {"gmail": "Gmail", "phone": "iPhone", "ocr": "Đọc ảnh", "statement": "Sao kê", "push": "Ghi lên Sheet",
               "server": "Lỗi máy chủ"}
THEME_LABEL = {"light": "Sáng", "dark": "Tối", "system": "Theo máy"}
# Six or more digits, possibly grouped by spaces, dots or dashes: card and account numbers (and big amounts).
_LONG_NUMBER = re.compile(r"\d(?:[ .\-]?\d){5,}")


def sharing(conn: sqlite3.Connection) -> bool:
    return db.get_setting(conn, "share_usage", "1") == "1"


def mask(text: str) -> str:
    return _LONG_NUMBER.sub(lambda m: re.sub(r"\d", "•", m.group()), str(text))


def record(conn: sqlite3.Connection, kind: str, detail: str = "", min_gap_s: int = 0) -> None:
    """Nothing is recorded while sharing is off. `min_gap_s` drops a repeat of the same kind (a page that reloads)."""
    if not sharing(conn):
        return
    if min_gap_s and conn.execute("SELECT 1 FROM usage_events WHERE kind = ? AND detail = ? AND "
                                  "at > datetime('now', 'localtime', ?)", (kind, detail, f"-{min_gap_s} seconds")).fetchone():
        return
    conn.execute("INSERT INTO usage_events(at, kind, detail) VALUES (datetime('now', 'localtime'), ?, ?)",
                 (kind, str(detail)[:300]))
    conn.execute("DELETE FROM usage_events WHERE at < datetime('now', 'localtime', ?)", (f"-{KEEP_DAYS} days",))


def record_error(conn: sqlite3.Connection, where: str, message: str) -> None:
    msg = re.sub(r"\s+", " ", mask(message)).strip()[:200]
    record(conn, "error", f"{where}: {msg}", min_gap_s=600)  # a failing background push retries after every edit


def _count(conn, kind: str, days: int, like: str = "%") -> int:
    return conn.execute("SELECT COUNT(*) FROM usage_events WHERE kind = ? AND detail LIKE ? AND "
                        "at >= datetime('now', 'localtime', ?)", (kind, like, f"-{days} days")).fetchone()[0]


def _sum(conn, kind: str, days: int, prefix: str = "") -> int:
    """Events whose detail is "<n>" or "<prefix>:<n>"."""
    rows = conn.execute("SELECT detail FROM usage_events WHERE kind = ? AND detail LIKE ? AND "
                        "at >= datetime('now', 'localtime', ?)", (kind, prefix + "%", f"-{days} days")).fetchall()
    return sum(int(d.rsplit(":", 1)[-1]) for (d,) in rows if d.rsplit(":", 1)[-1].isdigit())


def _when(at: str) -> str:
    # "2026-11-03 10:05" would be turned into a date number by Sheets (column E is formatted #,##0); "lúc" keeps it text.
    return at[:10] + " lúc " + at[11:16] if at else ""


def rows(conn: sqlite3.Connection, device: str) -> list[list]:
    """The rows added to the mirror's summary; [] while sharing is off."""
    if not sharing(conn):
        return []
    month = datetime.now().strftime("%Y-%m")
    last = conn.execute("SELECT at, detail FROM usage_events WHERE kind = 'open' ORDER BY id DESC LIMIT 1").fetchone()
    shots = _count(conn, "screenshot", 30)
    found, saved = _sum(conn, "screenshot", 30), _sum(conn, "tx_add", 30, "screenshot:")
    activity = [
        ("Phiên bản app", last["detail"] if last else ""),
        ("Mở app gần nhất", _when(last["at"]) if last else ""),
        ("Số lần mở 7 ngày", _count(conn, "open", 7)),
        ("Số lần mở 30 ngày", _count(conn, "open", 30)),
        ("Đọc ảnh (30 ngày)", f"{shots} lần · đọc được {found} dòng · lưu {saved} dòng" if shots else 0),
        ("Khoản từ iPhone (30 ngày)", _sum(conn, "phone_sync", 30)),
        ("Đơn từ Gmail (30 ngày)", _sum(conn, "gmail_sync", 30)),
        ("Nhập sao kê (30 ngày)", _count(conn, "statement", 30)),
        ("Nhập tay (30 ngày)", _sum(conn, "tx_add", 30, "manual:")),
        ("Đặt ngân sách (30 ngày)", _count(conn, "budget_set", 30)),
        ("Xem ống heo (30 ngày)", _count(conn, "piggy_view", 30)),
        ("Xem Có gì mới (30 ngày)", _count(conn, "whatsnew_view", 30)),
        ("Giao diện", THEME_LABEL.get(db.get_setting(conn, "theme", "system"), "Theo máy")),
    ]
    out = [[device, month, "Hoạt động", name, value, ""] for name, value in activity]
    for r in conn.execute("SELECT at, detail FROM usage_events WHERE kind = 'error' ORDER BY id DESC LIMIT ?",
                          (ERRORS_SENT,)):
        where, _, msg = r["detail"].partition(": ")
        out.append([device, month, "Lỗi", f"{_when(r['at'])} · {WHERE_LABEL.get(where, where)}", msg, ""])
    return out


# ---------------------------------------------------------------- what the server sees (app.after_request)

ERROR_PATHS = {"/api/gmail": "gmail", "/api/phone": "phone", "/api/statements": "statement", "/api/screenshot": "ocr"}


def observe(conn: sqlite3.Connection, method: str, path: str, status: int, sent, reply, form=None,
            exc: str = "") -> None:
    """Turn one finished request into usage events. `sent`/`reply` are the request and response JSON (or None)."""
    reply = reply if isinstance(reply, (dict, list)) else {}
    if status >= 500:
        return record_error(conn, "server", f"{method} {path}: {exc or f'HTTP {status}'}")
    where = next((w for p, w in ERROR_PATHS.items() if path.startswith(p)), None)
    if status >= 400:
        first_password_ask = isinstance(reply, dict) and reply.get("need_password") and not (form or {}).get("password")
        if where and isinstance(reply, dict) and reply.get("error") and not first_password_ask:
            record_error(conn, where, reply["error"])
        return
    if method == "POST" and path == "/api/screenshot":
        for f in reply if isinstance(reply, list) else []:
            if f.get("error"):
                record_error(conn, "ocr", f["error"])
        record(conn, "screenshot", str(sum(len(f.get("candidates") or []) for f in reply if isinstance(f, dict))))
    elif method == "POST" and path == "/api/phone/sync":
        record(conn, "phone_sync", str(reply.get("imported", 0)))
    elif method == "POST" and path == "/api/gmail/sync":
        record(conn, "gmail_sync", str(reply.get("imported", 0)))
    elif method == "POST" and path == "/api/statements":
        record(conn, "statement")
    elif method == "POST" and path == "/api/transactions":
        by_source = {}
        for t in sent if isinstance(sent, list) else [sent] if isinstance(sent, dict) else []:
            by_source[t.get("source") or "manual"] = by_source.get(t.get("source") or "manual", 0) + 1
        for source, n in by_source.items():
            record(conn, "tx_add", f"{source}:{n}")
    elif method == "PATCH" and path.startswith("/api/categories/") and isinstance(sent, dict) and "budget" in sent:
        record(conn, "budget_set")
    elif method == "GET" and path == "/api/piggy":
        record(conn, "piggy_view", min_gap_s=60)  # refresh() reloads an open piggy page after every change
    elif method == "POST" and path == "/api/profile" and isinstance(sent, dict):
        if "theme" in sent:
            record(conn, "theme", str(sent["theme"]))
        if "seen_version" in sent and "onboarded" not in sent:  # only the "Có gì mới" window sends it alone
            record(conn, "whatsnew_view")
