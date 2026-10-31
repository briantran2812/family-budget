"""Read Shopee/TikTok order emails from Gmail over IMAP. The App Password lives in the macOS Keychain."""
import email
import email.policy
import imaplib
import json
import re
import sqlite3
import ssl

import certifi
import keyring
import keyring.errors

import db
import parsers
import rules

KEYRING_SERVICE = "family-budget-gmail"
DEFAULT_QUERY = "from:(shopee OR tiktok OR momo) newer_than:180d"
# A subject must contain one of these (unaccented) to be read at all — skips promotions cheaply.
SUBJECT_HINTS = ["don hang", "order", "thanh toan", "payment", "hoa don", "receipt", "xac nhan",
                 "dat hang", "huy", "hoan tien", "refund", "giao", "giao dich", "bien lai", "thanh cong",
                 "transaction", "chuyen tien", "nhan tien"]


class SyncError(Exception):
    pass


def accounts(conn: sqlite3.Connection) -> list[str]:
    raw = db.get_setting(conn, "gmail_accounts")
    if raw:
        return json.loads(raw)
    legacy = db.get_setting(conn, "gmail_address")  # first version kept a single address
    return [legacy] if legacy else []


def _login(address: str, password: str) -> imaplib.IMAP4_SSL:
    # certifi's CA bundle, not the system one: a packaged app built with Homebrew Python would otherwise
    # look for certificates under /opt/homebrew, which other Macs don't have.
    ctx = ssl.create_default_context(cafile=certifi.where())
    imap = imaplib.IMAP4_SSL("imap.gmail.com", ssl_context=ctx, timeout=30)
    try:
        imap.login(address, password)
    except imaplib.IMAP4.error as e:
        raise SyncError(f"Gmail từ chối đăng nhập {address}. Kiểm tra lại App Password "
                        f"(16 ký tự, không phải mật khẩu Gmail thường).") from e
    return imap


def add_account(conn: sqlite3.Connection, address: str, app_password: str) -> None:
    """Log in once to prove the password works, then remember it in the Keychain."""
    address = address.strip().lower()
    password = app_password.replace(" ", "").strip()
    if "@" not in address or len(password) < 16:
        raise SyncError("Cần địa chỉ Gmail và App Password đủ 16 ký tự.")
    try:
        _login(address, password).logout()
    except OSError as e:
        raise SyncError(f"Không kết nối được tới Gmail — kiểm tra mạng ({e}).") from e
    keyring.set_password(KEYRING_SERVICE, address, password)
    current = accounts(conn)
    if address not in current:
        db.set_setting(conn, "gmail_accounts", json.dumps(current + [address]))


def remove_account(conn: sqlite3.Connection, address: str) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, address)
    except keyring.errors.PasswordDeleteError:
        pass
    db.set_setting(conn, "gmail_accounts", json.dumps([a for a in accounts(conn) if a != address]))


def _all_mail_folder(imap: imaplib.IMAP4_SSL) -> str:
    # The folder name is localised ("[Gmail]/Tất cả thư"); find it by its \All flag instead.
    _, folders = imap.list()
    for raw in folders or []:
        line = raw.decode(errors="replace")
        if "\\All" in line:
            m = re.search(r'"([^"]+)"\s*$', line) or re.search(r"(\S+)\s*$", line)
            return m.group(1)
    return "INBOX"


def process(conn, compiled, message_id, received, sender, subject, body) -> tuple[str, int | None]:
    """Apply one email to the transactions table. Returns (status, transaction_id)."""
    norm_subject = rules.normalize(subject)
    if not any(h in norm_subject for h in SUBJECT_HINTS) or any(w in norm_subject for w in parsers.PROMO_WORDS):
        return "skipped", None
    platform = parsers.platform_of(sender)
    if platform == "momo":
        r = parsers.parse_payment_email(subject, body, platform, message_id)
    else:
        r = parsers.parse_order_email(subject, body, sender, message_id)
    source = r["platform"] if r["platform"] != "other" else "email"
    kind = r.get("kind", "expense")

    if r["status"] == "cancelled":
        row = None
        if r["order_id"]:
            row = conn.execute("SELECT id FROM transactions WHERE source = ? AND order_id = ?",
                               (source, r["order_id"])).fetchone()
            conn.execute("UPDATE transactions SET status = 'cancelled' WHERE source = ? AND order_id = ?",
                         (source, r["order_id"]))
        return "cancelled", row["id"] if row else None
    if r["status"] == "no_amount":
        return "no_amount", None

    row = conn.execute("SELECT id FROM transactions WHERE source = ? AND order_id = ?",
                       (source, r["order_id"])).fetchone()
    if row:  # Shopee sends several emails per order (placed, paid, shipped); count it once
        return "duplicate", row["id"]
    cid = rules.categorize(conn, r["description"], kind, compiled)
    tx_id = conn.execute(
        "INSERT INTO transactions(date, amount, kind, description, source, category_id, order_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (received, r["amount"], kind, r["description"][:300], source, cid, r["order_id"])).lastrowid
    return "imported", tx_id


def _fetch_new(conn: sqlite3.Connection, address: str, query: str) -> tuple[int, list]:
    password = keyring.get_password(KEYRING_SERVICE, address)
    if not password:
        raise SyncError(f"Mất App Password của {address} trong Keychain — xoá và thêm lại tài khoản.")
    imap = _login(address, password)
    try:
        imap.select(f'"{_all_mail_folder(imap)}"', readonly=True)
        typ, data = imap.uid("SEARCH", "X-GM-RAW", f'"{query}"')
        if typ != "OK":
            raise SyncError(f"Gmail không chấp nhận câu tìm kiếm: {query}")
        uids = data[0].split()

        known = {r[0] for r in conn.execute("SELECT message_id FROM emails")}
        new_uids = []
        for i in range(0, len(uids), 200):
            chunk = b",".join(uids[i:i + 200]).decode()
            _, resp = imap.uid("FETCH", chunk, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
            for item in resp:
                if not isinstance(item, tuple):
                    continue
                uid = re.search(rb"UID (\d+)", item[0]).group(1)
                mid = email.message_from_bytes(item[1]).get("Message-ID", "").strip() or f"{address}-uid-{uid.decode()}"
                if mid not in known:
                    new_uids.append((uid, mid))

        fetched = []
        for uid, mid in new_uids:
            _, resp = imap.uid("FETCH", uid.decode(), "(BODY.PEEK[])")
            raw = next(item[1] for item in resp if isinstance(item, tuple))
            msg = email.message_from_bytes(raw, policy=email.policy.default)
            part = msg.get_body(preferencelist=("html", "plain"))
            content = part.get_content() if part else ""
            body = parsers.html_to_text(content) if part and part.get_content_subtype() == "html" else content
            fetched.append((parsers.email_datetime(msg["Date"]), mid, str(msg["From"] or ""),
                            str(msg["Subject"] or ""), body))
        return len(uids), fetched
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def sync(conn: sqlite3.Connection) -> dict:
    addresses = accounts(conn)
    if not addresses:
        raise SyncError("Chưa kết nối tài khoản Gmail nào. Vào Cài đặt → Thêm tài khoản Gmail.")
    query = db.get_setting(conn, "gmail_query", DEFAULT_QUERY).replace('"', "")
    counts: dict = {"found": 0, "new": 0, "errors": []}
    fetched = []
    for address in addresses:
        try:
            found, new = _fetch_new(conn, address, query)
        except SyncError as e:  # one bad account must not block the others
            counts["errors"].append(str(e))
            continue
        except OSError:
            counts["errors"].append(f"Không kết nối được Gmail ({address}) — kiểm tra mạng Wi-Fi rồi thử lại.")
            continue
        counts["found"] += found
        fetched += new
    counts["new"] = len(fetched)

    compiled = rules.load(conn)
    for stamp, mid, sender, subject, body in sorted(fetched):  # oldest first: purchase before shipped/cancel
        received = stamp[:10]
        status, tx_id = process(conn, compiled, mid, received, sender, subject, body)
        conn.execute("INSERT OR REPLACE INTO emails(message_id, received, sender, subject, body, status, "
                     "transaction_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (mid, received, sender, subject, body if status != "skipped" else "", status, tx_id))
        counts[status] = counts.get(status, 0) + 1
    if len(counts["errors"]) < len(addresses):
        db.set_setting(conn, "gmail_last_sync", parsers.datetime.now().isoformat(timespec="minutes"))
    return counts


def reparse(conn: sqlite3.Connection) -> dict:
    """Re-run the parser over stored emails that produced nothing — after editing parsers.py."""
    counts: dict[str, int] = {}
    compiled = rules.load(conn)
    rows = conn.execute("SELECT * FROM emails WHERE status IN ('no_amount', 'cancelled') "
                        "ORDER BY received").fetchall()
    for r in rows:
        status, tx_id = process(conn, compiled, r["message_id"], r["received"], r["sender"],
                                r["subject"], r["body"] or "")
        conn.execute("UPDATE emails SET status = ?, transaction_id = ? WHERE message_id = ?",
                     (status, tx_id, r["message_id"]))
        counts[status] = counts.get(status, 0) + 1
    return counts
