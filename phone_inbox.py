"""Pull expenses entered on iPhone from the Google Sheet behind phone/Code.gs. The connection code lives in the Keychain."""
import json
import re
import sqlite3
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import certifi
import keyring
import keyring.errors

import db
import rules

KEYRING_SERVICE = "family-budget-phone"
KEYRING_USER = "connection"
CODE_RE = re.compile(r"^https://script\.google\.com/macros/s/[\w-]+/exec\?k=[0-9a-f]{16,64}$")


class InboxError(Exception):
    pass


def connected(conn: sqlite3.Connection) -> bool:
    return db.get_setting(conn, "phone_connected") == "1"


def _get(code: str, action: str) -> dict:
    url = f"{code}&{urllib.parse.urlencode({'a': action})}"
    ctx = ssl.create_default_context(cafile=certifi.where())  # see gmail_sync._login
    try:
        with urllib.request.urlopen(url, timeout=30, context=ctx) as r:  # follows Google's 302 to googleusercontent
            body = r.read().decode()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise InboxError(f"Không kết nối được tới Google — kiểm tra mạng ({e}).") from e
    try:
        data = json.loads(body)
    except ValueError as e:
        # A login page instead of JSON means the deployment is not "Who has access: Anyone".
        raise InboxError("Google không trả về dữ liệu. Kiểm tra bản Deploy: Execute as \"Me\", "
                         "Who has access \"Anyone\".") from e
    if not data.get("ok"):
        raise InboxError(f"Apps Script báo lỗi: {data.get('error', 'không rõ')}. Lấy lại mã kết nối bằng layMaKetNoi.")
    return data


def connect(conn: sqlite3.Connection, code: str) -> str:
    """Check the code against the live script, then keep it. Returns the Sheet's URL."""
    code = code.strip()
    if not CODE_RE.match(code):
        raise InboxError("Mã kết nối có dạng https://script.google.com/macros/s/…/exec?k=… — "
                         "chạy layMaKetNoi trong Apps Script rồi sao chép cả dòng.")
    sheet = _get(code, "ping").get("sheet", "")
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, code)
    db.set_setting(conn, "phone_connected", "1")
    db.set_setting(conn, "phone_sheet_url", sheet)
    return sheet


def disconnect(conn: sqlite3.Connection) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except keyring.errors.PasswordDeleteError:
        pass
    for key in ("phone_connected", "phone_sheet_url"):
        db.set_setting(conn, key, "")


def code(conn: sqlite3.Connection) -> str:
    """The connection code, for pasting into the iPhone Shortcut."""
    c = keyring.get_password(KEYRING_SERVICE, KEYRING_USER) if connected(conn) else None
    if not c:
        raise InboxError("Chưa kết nối Google Sheet.")
    return c


def apply_row(conn: sqlite3.Connection, compiled, row: dict) -> str:
    """One sheet row → transactions. Returns imported | duplicate | invalid."""
    rid = str(row.get("id") or "").strip()
    amount = row.get("amount")
    if not rid or not isinstance(amount, (int, float)) or amount != amount or amount <= 0:
        return "invalid"  # NaN arrives as null in JSON
    if conn.execute("SELECT 1 FROM transactions WHERE source = 'phone' AND order_id = ?", (rid,)).fetchone():
        return "duplicate"
    try:
        day = datetime.fromisoformat(str(row.get("time"))[:19]).date().isoformat()
    except ValueError:
        return "invalid"
    desc = (row.get("description") or "").strip()[:300]
    account = (row.get("account") or "").strip() or None
    cid = rules.categorize(conn, desc, "expense", compiled)
    # The same charge may already be in the app from a card statement ("Thêm vào app" in Đối chiếu): enrich it.
    added = conn.execute(
        "SELECT id FROM transactions WHERE source = 'statement' AND status = 'ok' AND kind = 'expense' AND amount = ? "
        "AND abs(julianday(date) - julianday(?)) <= 3 ORDER BY abs(julianday(date) - julianday(?)) LIMIT 1",
        (int(amount), day, day)).fetchone()
    if added:
        conn.execute("UPDATE transactions SET source = 'phone', order_id = ?, description = ?, category_id = ? "
                     "WHERE id = ?", (rid, desc, cid, added["id"]))
        return "imported"
    conn.execute("INSERT INTO transactions(date, amount, kind, description, source, category_id, order_id, pay_account) "
                 "VALUES (?, ?, 'expense', ?, 'phone', ?, ?, ?)", (day, int(amount), desc, cid, rid, account))
    return "imported"


def sync(conn: sqlite3.Connection) -> dict:
    rows = _get(code(conn), "list").get("rows", [])
    compiled = rules.load(conn)
    counts = {"imported": 0, "duplicate": 0, "invalid": 0}
    bad_rows = []
    for row in rows:
        status = apply_row(conn, compiled, row)
        counts[status] += 1
        if status == "invalid":
            bad_rows.append(row.get("row"))
    db.set_setting(conn, "phone_last_sync", datetime.now().strftime("%Y-%m-%d %H:%M"))
    return {"total": len(rows), **counts, "bad_rows": bad_rows[:20]}
