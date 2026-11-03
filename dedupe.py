"""One answer to "is this the same transaction?" for every import path: email, iPhone, Telegram and the Mac form.

Two typed entries are never merged automatically (two 45.000 ₫ lunches are both real): they are flagged for the user.
An email and a typed entry are merged when exactly one candidate fits; the email row is kept as status 'merged', so
"Tách ra" can undo it. Rules and examples: docs/DEDUPE.md.
"""
import sqlite3

import notifications
from rules import normalize

TYPED = ("manual", "phone", "telegram", "screenshot")
EMAIL = ("momo", "shopee", "tiktok", "email")
EMAIL_LABEL = {"momo": "Email MoMo", "shopee": "Email Shopee", "tiktok": "Email TikTok", "email": "Email"}
BEFORE, AFTER = 1, 3  # a typed entry is dated up to 1 day before the email (midnight) or 3 days after (typed late)


def wallet(pay: str | None) -> str | None:
    """momo | zalopay | shopeepay | cash | other, from the free-text "Trả bằng"; None when unknown."""
    n = normalize(pay or "")
    if not n:
        return None
    for key, words in (("momo", ("momo",)), ("zalopay", ("zalopay", "zalo pay")), ("shopeepay", ("shopeepay", "shopee pay")),
                       ("cash", ("tien mat", "cash", "tm"))):
        if any(w == n or w in n.split() or (" " in w and w in n) for w in words):
            return key
    return "other"


def compatible(email_source: str, pay: str | None) -> bool:
    """A MoMo email is a MoMo wallet payment: it never matches an entry paid in cash or by card."""
    w = wallet(pay)
    return w is None or email_source != "momo" or w == "momo"


def _rows(conn, sql, args):
    return [dict(r) for r in conn.execute(sql, args)]


def typed_candidates(conn: sqlite3.Connection, kind: str, amount: int, day: str, email_source: str) -> list[int]:
    """Typed entries an email dated `day` may be the record of."""
    rows = _rows(conn, f"SELECT id, pay_account FROM transactions WHERE source IN {TYPED} AND status = 'ok' "
                       "AND link_ref IS NULL AND dup_state IS NOT 'kept' AND kind = ? AND amount = ? "
                       "AND julianday(date) - julianday(?) BETWEEN ? AND ? ORDER BY abs(julianday(date) - julianday(?)), id",
                 (kind, amount, day, -BEFORE, AFTER, day))
    return [r["id"] for r in rows if compatible(email_source, r["pay_account"])]


def email_candidates(conn: sqlite3.Connection, kind: str, amount: int, day: str, pay: str | None) -> list[int]:
    """Email records a typed entry dated `day` may be the same payment as."""
    rows = _rows(conn, f"SELECT id, source FROM transactions WHERE source IN {EMAIL} AND status = 'ok' "
                       "AND link_ref IS NULL AND dup_state IS NOT 'kept' AND kind = ? AND amount = ? "
                       "AND julianday(?) - julianday(date) BETWEEN ? AND ? ORDER BY abs(julianday(date) - julianday(?)), id",
                 (kind, amount, day, -BEFORE, AFTER, day))
    return [r["id"] for r in rows if compatible(r["source"], pay)]


def merge(conn: sqlite3.Connection, typed_id: int, email_id: int) -> None:
    """The typed entry stays (its description and category are the user's); the email row is kept out of every total."""
    e = conn.execute("SELECT source, order_id, pay_account FROM transactions WHERE id = ?", (email_id,)).fetchone()
    pay = e["pay_account"] or ("Ví MoMo" if e["source"] == "momo" else None)
    conn.execute("UPDATE transactions SET link_ref = ?, dup_with = ?, dup_state = NULL, "
                 "pay_account = COALESCE(pay_account, ?) WHERE id = ?",
                 (f"{e['source']}:{e['order_id'] or email_id}", email_id, pay, typed_id))
    conn.execute("UPDATE transactions SET status = 'merged', dup_with = ?, dup_state = NULL WHERE id = ?",
                 (typed_id, email_id))


def split(conn: sqlite3.Connection, tx_id: int) -> bool:
    """Undo a merge from either side: both count again and are never matched to each other again."""
    t = conn.execute("SELECT id, status, dup_with, link_ref FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not t or not t["dup_with"]:
        return False
    typed_id, email_id = (t["dup_with"], t["id"]) if t["status"] == "merged" else (t["id"], t["dup_with"])
    conn.execute("UPDATE transactions SET link_ref = NULL, dup_state = 'kept' WHERE id = ?", (typed_id,))
    conn.execute("UPDATE transactions SET status = 'ok', dup_state = 'kept' WHERE id = ? AND status = 'merged'", (email_id,))
    return True


def typed_twin(conn: sqlite3.Connection, tx_id: int) -> int | None:
    """Another typed entry of the same amount and day by someone else, or through another channel: maybe the same payment."""
    t = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not t or t["source"] not in TYPED or t["status"] != "ok" or t["dup_state"]:
        return None
    row = conn.execute(f"SELECT id FROM transactions WHERE id != ? AND source IN {TYPED} AND status = 'ok' "
                       "AND dup_state IS NULL AND kind = ? AND amount = ? AND date = ? "
                       "AND (entered_by IS NOT ? OR source != ?) ORDER BY id DESC LIMIT 1",
                       (tx_id, t["kind"], t["amount"], t["date"], t["entered_by"], t["source"])).fetchone()
    return row["id"] if row else None


def describe(conn: sqlite3.Connection, tx_id: int) -> str:
    t = conn.execute("SELECT date, amount, description, entered_by, source FROM transactions WHERE id = ?",
                     (tx_id,)).fetchone()
    who = t["entered_by"] or EMAIL_LABEL.get(t["source"], t["source"])
    return f"{t['amount']:,} ₫".replace(",", ".") + (f" · {t['description']}" if t["description"] else "") + \
        f" ({who}, {t['date'][8:]}/{t['date'][5:7]})"


def flag(conn: sqlite3.Connection, tx_id: int, other_id: int, count: bool = True) -> None:
    """Ask the user. `count=False` keeps the new row out of the totals until they answer (an email that fits several)."""
    conn.execute("UPDATE transactions SET dup_state = 'open', dup_with = ?" + ("" if count else ", status = 'cancelled'") +
                 " WHERE id = ?", (other_id, tx_id))
    conn.execute("UPDATE transactions SET dup_state = 'open', dup_with = ? WHERE id = ? AND dup_state IS NULL",
                 (tx_id, other_id))
    notifications.add(conn, "duplicate", "⚠️", "Có thể trùng: " + describe(conn, tx_id),
                      "Giống " + describe(conn, other_id) + ". Bấm để xem và chọn.", link={"tx": tx_id},
                      dedupe=f"dup:{min(tx_id, other_id)}:{max(tx_id, other_id)}")


def check_typed(conn: sqlite3.Connection, tx_id: int) -> str:
    """After a typed entry is saved: merge it with the one email it matches, or flag a possible duplicate.
    Returns merged | flagged | unique."""
    t = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not t or t["status"] != "ok":
        return "unique"
    if t["source"] in EMAIL:
        return check_email(conn, tx_id)
    if t["source"] not in TYPED:
        return "unique"
    emails = email_candidates(conn, t["kind"], t["amount"], t["date"], t["pay_account"])
    if len(emails) == 1:
        merge(conn, tx_id, emails[0])
        return "merged"
    if emails:
        flag(conn, tx_id, emails[0])
        return "flagged"
    twin = typed_twin(conn, tx_id)
    if twin:
        flag(conn, tx_id, twin)
        return "flagged"
    return "unique"


def check_email(conn: sqlite3.Connection, tx_id: int) -> str:
    """After an email record is saved: fold it into the one typed entry it matches, or hold it for the user."""
    t = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not t or t["status"] != "ok" or t["source"] not in EMAIL:
        return "unique"
    typed = typed_candidates(conn, t["kind"], t["amount"], t["date"], t["source"])
    if len(typed) == 1:
        merge(conn, typed[0], tx_id)
        return "merged"
    if typed:
        flag(conn, tx_id, typed[0], count=False)
        return "flagged"
    return "unique"


def resolve(conn: sqlite3.Connection, tx_id: int, action: str, other: int | None = None) -> None:
    """keep: both are real · drop: this one is the duplicate · merge: this email is the record of `other`."""
    t = conn.execute("SELECT id, dup_with, source FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not t:
        return
    if action == "merge" and other:
        typed_id, email_id = (other, tx_id) if t["source"] in EMAIL else (tx_id, other)
        conn.execute("UPDATE transactions SET status = 'ok' WHERE id = ?", (tx_id,))
        _close(conn, tx_id)
        merge(conn, typed_id, email_id)
        return
    if action == "keep":
        conn.execute("UPDATE transactions SET status = 'ok' WHERE id = ? AND status = 'cancelled' AND dup_state = 'open'",
                     (tx_id,))
    elif action == "drop":
        conn.execute("UPDATE transactions SET status = 'cancelled' WHERE id = ?", (tx_id,))
    _close(conn, tx_id)


def _close(conn, tx_id):
    """Marks the pair answered; a partner still flagged for a third entry stays open."""
    t = conn.execute("SELECT dup_with FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    conn.execute("UPDATE transactions SET dup_state = 'kept' WHERE id = ?", (tx_id,))
    if t and t["dup_with"]:
        conn.execute("UPDATE transactions SET dup_state = 'kept' WHERE id = ? AND dup_with = ? AND dup_state = 'open'",
                     (t["dup_with"], tx_id))


def candidates(conn: sqlite3.Connection, tx_id: int) -> list[dict]:
    """What an open entry may duplicate, for the dialog: the flagged partner first."""
    t = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not t:
        return []
    if t["source"] in EMAIL:
        ids = typed_candidates(conn, t["kind"], t["amount"], t["date"], t["source"])
    else:
        ids = email_candidates(conn, t["kind"], t["amount"], t["date"], t["pay_account"])
    if t["dup_with"] and t["dup_with"] not in ids:
        ids.insert(0, t["dup_with"])
    return [{"id": i, "text": describe(conn, i)} for i in ids
            if conn.execute("SELECT 1 FROM transactions WHERE id = ?", (i,)).fetchone()]
