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
# Google Workspace accounts get /a/macros/<domain>/s/…; a signed-in browser may add /u/<n>/.
# Code.gs SCRIPT_VERSION this app needs; an older deployed script gets a warning in the app (docs/DEPLOY.md E).
REQUIRED_SCRIPT_VERSION = 2
CODE_RE = re.compile(r"^https://script\.google\.com/(?:a/)?macros/(?:[\w.-]+/)?(?:u/\d+/)?s/[\w-]+/exec\?k=[0-9a-f]{16,64}$")


class InboxError(Exception):
    pass


def connected(conn: sqlite3.Connection) -> bool:
    return db.get_setting(conn, "phone_connected") == "1"


def _get(code: str, action: str, **params) -> dict:
    return _request(f"{code}&{urllib.parse.urlencode({'a': action, **params})}")


def _post(code: str, payload: dict) -> dict:
    # Apps Script runs doPost, then answers 302; urllib follows it as a GET without the body, which is what Google expects.
    return _request(code, json.dumps(payload, ensure_ascii=False).encode())


def _request(url: str, data: bytes | None = None) -> dict:
    ctx = ssl.create_default_context(cafile=certifi.where())  # see gmail_sync._login
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:  # follows Google's 302 to googleusercontent
            body, final = r.read().decode(errors="replace"), r.geturl()
    except urllib.error.HTTPError as e:  # Google answers some script errors with 4xx/5xx and an HTML page
        body, final = e.read().decode(errors="replace"), e.geturl()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise InboxError(f"Không kết nối được tới Google — kiểm tra mạng ({e}).") from e
    try:
        data = json.loads(body)
    except ValueError:
        raise InboxError(_explain_html(body, final)) from None
    if not data.get("ok"):
        raise InboxError(f"Apps Script báo lỗi: {data.get('error', 'không rõ')}. Lấy lại mã kết nối bằng layMaKetNoi.")
    return data


def _explain_html(body: str, final_url: str) -> str:
    """Google sent a web page instead of JSON; say which setup step it points to."""
    if "accounts.google.com" in final_url or "ServiceLogin" in body:
        return ("Google đòi đăng nhập: bản Deploy chưa mở cho mọi người. Deploy → Manage deployments → ✏️ → "
                "Who has access: Anyone → Deploy.")
    if "Script function not found: doPost" in body or "tìm thấy hàm tập lệnh: doPost" in body:  # English / Vietnamese UI
        return ("Code.gs trên Google là bản cũ, chưa nhận được bản sao từ Mac. Dán Code.gs mới, ⌘S, rồi "
                "Deploy → Manage deployments → ✏️ → Version: New version → Deploy.")
    if "Authorization is required" in body or "Cần được cấp quyền" in body:
        return ("Code.gs mới cần thêm quyền mà chưa được cho phép. Mở Apps Script, chọn batQuetEmail → ▶ Run → "
                "Allow, rồi Deploy → Manage deployments → ✏️ → Version: New version → Deploy.")
    if "Script function not found: doGet" in body or "tìm thấy hàm tập lệnh: doGet" in body:
        return ("Bản Deploy không có code (đã Deploy trước khi dán Code.gs, hoặc chưa lưu). Dán Code.gs, ⌘S, rồi "
                "Deploy → Manage deployments → ✏️ → Version: New version → Deploy.")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style).*?</\1>", " ", body))).strip()
    return f"Google không trả về dữ liệu mà trả về trang: “{text[:200]}”"


def connect(conn: sqlite3.Connection, code: str) -> str:
    """Check the code against the live script, then keep it. Returns the Sheet's URL."""
    code = code.strip()
    if "/home/projects/" in code or code.rstrip("/").endswith("/edit"):
        raise InboxError("Đây là địa chỉ trang soạn code, chưa phải mã kết nối. Trong Apps Script chọn hàm layMaKetNoi "
                         "→ ▶ Run, rồi sao chép dòng https://script.google.com/macros/s/…/exec?k=… trong Execution log.")
    if code.endswith("/exec"):
        raise InboxError("Thiếu phần ?k=… ở cuối. Chạy layMaKetNoi và sao chép cả dòng trong Execution log.")
    if not CODE_RE.match(code):
        raise InboxError("Mã kết nối có dạng https://script.google.com/macros/s/…/exec?k=… — "
                         "chạy layMaKetNoi trong Apps Script rồi sao chép cả dòng.")
    reply = _get(code, "ping")
    sheet = reply.get("sheet", "")
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, code)
    db.set_setting(conn, "phone_connected", "1")
    db.set_setting(conn, "phone_sheet_url", sheet)
    _remember_script(conn, reply)
    return sheet


def _remember_script(conn: sqlite3.Connection, reply: dict) -> None:
    """Sheet name (shows which environment this Mac is on) and Code.gs version; scripts before 2 send neither."""
    if reply.get("name"):
        db.set_setting(conn, "phone_sheet_name", str(reply["name"]))
    db.set_setting(conn, "phone_script_version", str(int(reply.get("version") or 1)))


def environment(conn: sqlite3.Connection) -> dict:
    """For /api/info: which Sheet this Mac talks to, and whether its Code.gs is older than this app needs."""
    name = db.get_setting(conn, "phone_sheet_name")
    version = int(db.get_setting(conn, "phone_script_version") or 0)
    return {"phone_sheet_name": name, "phone_script_version": version,
            "phone_script_required": REQUIRED_SCRIPT_VERSION,
            "phone_script_outdated": connected(conn) and version < REQUIRED_SCRIPT_VERSION,
            "phone_env_test": bool(re.search(r"\btest", name, re.I))}


def disconnect(conn: sqlite3.Connection) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except keyring.errors.PasswordDeleteError:
        pass
    for key in ("phone_connected", "phone_sheet_url", "phone_sheet_name", "phone_script_version"):
        db.set_setting(conn, key, "")
    import sheet_email
    sheet_email.forget(conn)


def code(conn: sqlite3.Connection) -> str:
    """The connection code, for pasting into the iPhone Shortcut."""
    c = keyring.get_password(KEYRING_SERVICE, KEYRING_USER) if connected(conn) else None
    if not c:
        raise InboxError("Chưa kết nối Google Sheet.")
    return c


def category_of(conn: sqlite3.Connection, chosen: str | None) -> tuple[int, str] | None:
    """(id, kind) of the category picked on the phone ("🛒 Ăn uống & đi chợ"), matched without emoji, accents or case."""
    name = rules.normalize(re.sub(r"^[^\wÀ-ỹ]+", "", chosen or ""))
    if not name:
        return None
    for cid, cname, kind in conn.execute("SELECT id, name, kind FROM categories"):
        if rules.normalize(cname) == name:
            return cid, kind
    return None


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
    picked = category_of(conn, row.get("category"))
    kind = picked[1] if picked else "expense"
    cid = picked[0] if picked else rules.categorize(conn, desc, "expense", compiled)
    # The same charge may already be in the app from a card statement ("Thêm vào app" in Đối chiếu): enrich it.
    added = conn.execute(
        "SELECT id FROM transactions WHERE source = 'statement' AND status = 'ok' AND kind = ? AND amount = ? "
        "AND abs(julianday(date) - julianday(?)) <= 3 ORDER BY abs(julianday(date) - julianday(?)) LIMIT 1",
        (kind, int(amount), day, day)).fetchone()
    if added:
        conn.execute("UPDATE transactions SET source = 'phone', order_id = ?, description = ?, category_id = ? "
                     "WHERE id = ?", (rid, desc, cid, added["id"]))
        return "imported"
    conn.execute("INSERT INTO transactions(date, amount, kind, description, source, category_id, order_id, pay_account) "
                 "VALUES (?, ?, ?, ?, 'phone', ?, ?, ?)", (day, int(amount), kind, desc, cid, rid, account))
    return "imported"


def sync(conn: sqlite3.Connection) -> dict:
    """iPhone rows, then (Code.gs 3+) the Gmail copies in the "Email" tab; an email failure never fails the iPhone part."""
    import sheet_email
    reply = _get(code(conn), "list")
    _remember_script(conn, reply)
    rows = reply.get("rows", [])
    compiled = rules.load(conn)
    counts = {"imported": 0, "duplicate": 0, "invalid": 0}
    bad_rows = []
    for row in rows:
        status = apply_row(conn, compiled, row)
        counts[status] += 1
        if status == "invalid":
            bad_rows.append(row.get("row"))
    db.set_setting(conn, "phone_last_sync", datetime.now().strftime("%Y-%m-%d %H:%M"))
    result = {"total": len(rows), **counts, "bad_rows": bad_rows[:20], "emails_imported": 0}
    if sheet_email.available(conn):
        try:
            result["emails"] = sheet_email.pull(conn, code(conn))
            result["emails_imported"] = result["emails"].get("imported", 0)
        except InboxError as e:
            db.set_setting(conn, "sheet_email_error", str(e))
            result["emails_error"] = str(e)
    return result


# ---------------------------------------------------------------- mirror to the Sheet (tabs "Giao dịch", "Tổng hợp")

SRC_LABEL = {"shopee": "Shopee", "tiktok": "TikTok", "momo": "MoMo", "manual": "Nhập tay", "phone": "iPhone",
             "screenshot": "Ảnh chụp", "statement": "Sao kê", "email": "Email"}


def device_name(conn: sqlite3.Connection) -> str:
    name = db.get_setting(conn, "device_name")
    if name:
        return name
    import subprocess
    try:
        name = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        name = ""
    import socket
    return name or socket.gethostname()


def push_enabled(conn: sqlite3.Connection) -> bool:
    return connected(conn) and db.get_setting(conn, "phone_push", "1") == "1"


def mirror_payload(conn: sqlite3.Connection) -> dict:
    device = device_name(conn)
    txs = conn.execute(
        "SELECT t.id, t.date, t.kind, t.amount, t.description, c.name AS category, t.pay_account, t.source, t.status "
        "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id ORDER BY t.date DESC, t.id DESC").fetchall()
    rows = [[t["date"], "Thu" if t["kind"] == "income" else "Chi", t["amount"], t["description"],
             t["category"] or "Chưa phân loại", t["pay_account"] or "", SRC_LABEL.get(t["source"], t["source"]),
             "Có" if t["status"] == "ok" else "Không", device, t["id"]] for t in txs]
    summary = []
    piggy = dict(conn.execute("SELECT month, saved FROM piggy").fetchall())
    for (month,) in conn.execute("SELECT DISTINCT substr(date, 1, 7) FROM transactions WHERE status = 'ok' "
                                 "ORDER BY 1 DESC LIMIT 24").fetchall():
        def total(sql, *args):
            return conn.execute(sql, (month, *args)).fetchall()
        tot = dict(total("SELECT kind, SUM(amount) FROM transactions WHERE status = 'ok' AND substr(date, 1, 7) = ? "
                         "GROUP BY kind"))
        income, expense = tot.get("income", 0), tot.get("expense", 0)
        pct = lambda v: round(v / expense, 4) if expense else ""
        summary += [[device, month, "Tổng", "Thu nhập", income, ""], [device, month, "Tổng", "Tổng chi", expense, pct(expense)],
                    [device, month, "Tổng", "Còn lại", income - expense, ""]]
        if month in piggy:
            summary.append([device, month, "Ống heo", "Bỏ ống heo", piggy[month], ""])
        for name, amount in total("SELECT COALESCE(c.name, 'Chưa phân loại'), SUM(t.amount) FROM transactions t "
                                  "LEFT JOIN categories c ON c.id = t.category_id WHERE t.status = 'ok' AND t.kind = 'expense' "
                                  "AND substr(t.date, 1, 7) = ? GROUP BY 1 ORDER BY 2 DESC"):
            summary.append([device, month, "Hạng mục", name, amount, pct(amount)])
        for name, amount in total("SELECT COALESCE(pay_account, 'Chưa ghi cách trả'), SUM(amount) FROM transactions "
                                  "WHERE status = 'ok' AND kind = 'expense' AND substr(date, 1, 7) = ? GROUP BY 1 ORDER BY 2 DESC"):
            summary.append([device, month, "Cách trả", name, amount, pct(amount)])
    import usage
    summary += usage.rows(conn, device)  # groups "Hoạt động" and "Lỗi"; none while share_usage is off
    return {"a": "mirror", "device": device, "rows": rows, "summary": summary}


def push(conn: sqlite3.Connection) -> dict:
    """Replace this Mac's rows in the Sheet. The app stays the source of truth; edits made in the Sheet are overwritten."""
    try:
        r = _post(code(conn), mirror_payload(conn))
    except InboxError as e:
        db.set_setting(conn, "phone_push_error", str(e))
        import notifications
        notifications.add(conn, "error", "⚠️", "Không ghi được bản sao lên Google Sheet", str(e),
                          link={"tab": "settings"}, dedupe=f"push-error:{datetime.now():%Y-%m-%d}")
        conn.commit()  # the caller's transaction is rolled back by the exception
        raise
    db.set_setting(conn, "phone_push_error", "")
    db.set_setting(conn, "phone_last_push", datetime.now().strftime("%Y-%m-%d %H:%M"))
    return r
