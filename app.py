"""Thu chi gia đình — local web app.

Desktop: `python desktop.py` (native window). Browser: `python app.py` → http://127.0.0.1:8765
"""
import argparse
import csv
import io
import os
import subprocess
import sys
import tempfile
import threading
from datetime import date
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

import alerts
import db
import gmail_sync
import notifications
import parsers
import phone_inbox
import piggy
import reconcile
import rules
import statements

VERSION = "1.4.0"
RESOURCES = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # PyInstaller unpacks data files here
app = Flask(__name__, static_folder=str(RESOURCES / "static"))
app.config["DESKTOP"] = False


@app.before_request
def guard():
    # Only this machine's browser may talk to the app: a web page can't set a custom header on a
    # cross-site request, and a rebinding DNS name won't match the Host check.
    if request.host.split(":")[0] not in ("127.0.0.1", "localhost"):
        abort(403)
    if request.method not in ("GET", "HEAD") and request.headers.get("X-Budget") != "1":
        abort(403)


def conn():
    return db.connect()


def month_bounds(month: str) -> tuple[str, str]:
    y, m = map(int, month.split("-"))
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date(y, m, 1).isoformat(), nxt.isoformat()


def prev_month(month: str) -> str:
    y, m = map(int, month.split("-"))
    return f"{y - (m == 1)}-{(m - 2) % 12 + 1:02d}"


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------------------------------------------------------------- profile & app info

@app.get("/api/info")
def info():
    with conn() as c:
        return jsonify(version=VERSION, desktop=app.config["DESKTOP"], data_dir=str(db.DB_PATH.parent),
                       user_name=db.get_setting(c, "user_name"),
                       onboarded=db.get_setting(c, "onboarded") == "1",
                       seen_version=db.get_setting(c, "seen_version"),
                       theme=db.get_setting(c, "theme", "system"),
                       gmail_accounts=gmail_sync.accounts(c),
                       gmail_query=db.get_setting(c, "gmail_query", gmail_sync.DEFAULT_QUERY),
                       gmail_last_sync=db.get_setting(c, "gmail_last_sync"),
                       phone_connected=phone_inbox.connected(c),
                       phone_sheet_url=db.get_setting(c, "phone_sheet_url"),
                       phone_last_sync=db.get_setting(c, "phone_last_sync"),
                       phone_push=db.get_setting(c, "phone_push", "1") == "1",
                       phone_last_push=db.get_setting(c, "phone_last_push"),
                       phone_push_error=db.get_setting(c, "phone_push_error"),
                       device_name=phone_inbox.device_name(c))


@app.get("/api/notifications")
def list_notifications():
    with conn() as c:
        if db.get_setting(c, "onboarded") == "1":  # announce each version once; new users get the welcome instead
            notifications.add(c, "version", "✨", f"Phiên bản {VERSION}: xem có gì mới", link={"whatsnew": True},
                              dedupe=f"version:{VERSION}")
        piggy.record_due(c)  # the bell is read when the app opens, so a month that just closed shows up in it
        return jsonify(notifications.listing(c))


@app.post("/api/notifications/read")
def read_notifications():
    with conn() as c:
        notifications.mark_read(c, (request.get_json(silent=True) or {}).get("id"))
    return jsonify(ok=True)


@app.post("/api/profile")
def profile():
    data = request.get_json()
    with conn() as c:
        for key in ("user_name", "onboarded", "gmail_query", "phone_push", "device_name", "seen_version", "theme"):
            if key in data:
                db.set_setting(c, key, str(data[key]).strip())
    return jsonify(ok=True)


@app.post("/api/reveal-data")
def reveal_data():
    subprocess.run(["open", str(db.DB_PATH.parent)], check=False)
    return jsonify(ok=True)


@app.post("/api/shutdown")
def shutdown():
    threading.Timer(0.3, lambda: os._exit(0)).start()  # let the response reach the browser first
    return jsonify(ok=True)


# ---------------------------------------------------------------- categories & rules

@app.get("/api/categories")
def list_categories():
    with conn() as c:
        cats = [dict(r) for r in c.execute("SELECT * FROM categories ORDER BY kind DESC, sort, name")]
        for cat in cats:
            cat["keywords"] = [r[0] for r in c.execute(
                "SELECT keyword FROM rules WHERE category_id = ? ORDER BY keyword", (cat["id"],))]
    return jsonify(cats)


@app.post("/api/categories")
def add_category():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="Cần tên hạng mục"), 400
    with conn() as c:
        sort = c.execute("SELECT COALESCE(MAX(sort), 0) + 1 FROM categories").fetchone()[0]
        c.execute("INSERT OR IGNORE INTO categories(name, kind, sort, icon) VALUES (?, ?, ?, ?)",
                  (name, data.get("kind", "expense"), sort, data.get("icon") or "📦"))
    return jsonify(ok=True)


@app.patch("/api/categories/<int:cid>")
def update_category(cid):
    data = request.get_json()
    allowed = {k: data[k] for k in ("name", "icon", "budget") if k in data}
    if "budget" in allowed:
        allowed["budget"] = int(allowed["budget"]) if allowed["budget"] else None
    if not allowed:
        abort(400)
    with conn() as c:
        c.execute(f"UPDATE categories SET {', '.join(f'{k} = ?' for k in allowed)} WHERE id = ?",
                  (*allowed.values(), cid))
    return jsonify(ok=True)


@app.delete("/api/categories/<int:cid>")
def delete_category(cid):
    with conn() as c:
        c.execute("DELETE FROM categories WHERE id = ?", (cid,))
    return jsonify(ok=True)


@app.post("/api/rules")
def add_rule():
    data = request.get_json()
    kw = rules.normalize(data.get("keyword", ""))
    if len(kw) < 2:
        return jsonify(error="Từ khoá quá ngắn"), 400
    with conn() as c:
        c.execute("INSERT INTO rules(keyword, category_id) VALUES (?, ?) "
                  "ON CONFLICT(keyword) DO UPDATE SET category_id = excluded.category_id",
                  (kw, data["category_id"]))
        changed = 0
        if data.get("apply_existing"):
            compiled = rules.load(c)
            for t in c.execute("SELECT id, description, kind FROM transactions").fetchall():
                if kw in rules.normalize(t["description"]):
                    new = rules.categorize(c, t["description"], t["kind"], compiled)
                    changed += c.execute("UPDATE transactions SET category_id = ? WHERE id = ? "
                                         "AND category_id IS NOT ?", (new, t["id"], new)).rowcount
    return jsonify(ok=True, changed=changed)


@app.delete("/api/rules/<path:keyword>")
def delete_rule(keyword):
    with conn() as c:
        c.execute("DELETE FROM rules WHERE keyword = ?", (keyword,))
    return jsonify(ok=True)


# ---------------------------------------------------------------- transactions

TX_SELECT = ("SELECT t.*, c.name AS category, c.icon AS icon FROM transactions t "
             "LEFT JOIN categories c ON c.id = t.category_id ")


@app.get("/api/transactions")
def list_transactions():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    start, end = month_bounds(month)
    with conn() as c:
        rows = c.execute(TX_SELECT + "WHERE t.date >= ? AND t.date < ? ORDER BY t.date DESC, t.id DESC",
                         (start, end)).fetchall()
    return jsonify([dict(r) for r in rows])


def _insert(c, t: dict) -> int:
    kind = t.get("kind", "expense")
    amount = int(t["amount"])
    if amount <= 0:
        raise ValueError("Số tiền phải lớn hơn 0")
    cid = t.get("category_id") or rules.categorize(c, t.get("description", ""), kind)
    return c.execute(
        "INSERT INTO transactions(date, amount, kind, description, source, category_id, pay_account) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (t.get("date") or date.today().isoformat(), amount, kind, (t.get("description") or "").strip(),
         t.get("source", "manual"), cid, (t.get("pay_account") or "").strip() or None)).lastrowid


@app.post("/api/transactions")
def add_transactions():
    data = request.get_json()
    items = data if isinstance(data, list) else [data]
    try:
        with conn() as c:
            ids = [_insert(c, t) for t in items]
    except (KeyError, ValueError) as e:
        return jsonify(error=str(e)), 400
    return jsonify(ok=True, ids=ids)


@app.get("/api/transactions/<int:tid>")
def get_transaction(tid):
    with conn() as c:
        row = c.execute(TX_SELECT + "WHERE t.id = ?", (tid,)).fetchone()
    return jsonify(dict(row)) if row else abort(404)


@app.patch("/api/transactions/<int:tid>")
def update_transaction(tid):
    data = request.get_json()
    allowed = {k: data[k] for k in ("date", "amount", "kind", "description", "category_id", "status", "pay_account")
               if k in data}
    if "pay_account" in allowed:
        allowed["pay_account"] = (allowed["pay_account"] or "").strip() or None
    if not allowed:
        abort(400)
    with conn() as c:
        c.execute(f"UPDATE transactions SET {', '.join(f'{k} = ?' for k in allowed)} WHERE id = ?",
                  (*allowed.values(), tid))
    return jsonify(ok=True)


@app.delete("/api/transactions/<int:tid>")
def delete_transaction(tid):
    with conn() as c:
        c.execute("DELETE FROM transactions WHERE id = ?", (tid,))
    return jsonify(ok=True)


@app.get("/api/export.csv")
def export_csv():
    with conn() as c:
        rows = c.execute(
            "SELECT t.date, t.kind, t.amount, c.name AS category, t.description, t.source, t.order_id, t.status "
            "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id ORDER BY t.date").fetchall()
    buf = io.StringIO()
    buf.write("﻿")  # Excel needs the BOM to read Vietnamese as UTF-8
    w = csv.writer(buf)
    w.writerow(["Ngày", "Loại", "Số tiền", "Hạng mục", "Mô tả", "Nguồn", "Mã đơn", "Trạng thái"])
    w.writerows([tuple(r) for r in rows])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=thu-chi-{date.today()}.csv"})


# ---------------------------------------------------------------- summary

@app.get("/api/summary")
def summary():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    start, end = month_bounds(month)
    pstart, pend = month_bounds(prev_month(month))
    ok = "status = 'ok'"
    with conn() as c:
        totals = dict(c.execute(
            f"SELECT kind, SUM(amount) FROM transactions WHERE {ok} AND date >= ? AND date < ? GROUP BY kind",
            (start, end)).fetchall())
        count = c.execute(f"SELECT COUNT(*) FROM transactions WHERE {ok} AND date >= ? AND date < ?",
                          (start, end)).fetchone()[0]
        by_cat = c.execute(
            f"SELECT c.id, COALESCE(c.name, 'Chưa phân loại') AS name, COALESCE(c.icon, '❔') AS icon, c.budget, "
            f"SUM(t.amount) AS amount, COUNT(*) AS n "
            f"FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
            f"WHERE t.{ok} AND t.kind = 'expense' AND t.date >= ? AND t.date < ? "
            f"GROUP BY c.id ORDER BY amount DESC", (start, end)).fetchall()
        prev = dict(c.execute(
            f"SELECT category_id, SUM(amount) FROM transactions WHERE {ok} AND kind = 'expense' "
            f"AND date >= ? AND date < ? GROUP BY category_id", (pstart, pend)).fetchall())
        by_source = dict(c.execute(
            f"SELECT source, SUM(amount) FROM transactions WHERE {ok} AND kind = 'expense' "
            f"AND date >= ? AND date < ? GROUP BY source", (start, end)).fetchall())
        by_pay = c.execute(
            f"SELECT pay_account AS name, SUM(amount) AS amount, COUNT(*) AS count FROM transactions "
            f"WHERE {ok} AND kind = 'expense' AND date >= ? AND date < ? GROUP BY pay_account ORDER BY amount DESC",
            (start, end)).fetchall()
        recent = c.execute(TX_SELECT + "WHERE t.date >= ? AND t.date < ? ORDER BY t.date DESC, t.id DESC LIMIT 6",
                           (start, end)).fetchall()
        trend = []
        m = month
        for _ in range(12):
            s, e = month_bounds(m)
            row = c.execute(f"SELECT COALESCE(SUM(CASE WHEN kind='expense' THEN amount END), 0), "
                            f"COALESCE(SUM(CASE WHEN kind='income' THEN amount END), 0) "
                            f"FROM transactions WHERE {ok} AND date >= ? AND date < ?", (s, e)).fetchone()
            trend.append({"month": m, "expense": row[0], "income": row[1]})
            m = prev_month(m)
        budget_alerts = alerts.budget_alerts(c, month)
    expense = totals.get("expense", 0)
    return jsonify(
        month=month, expense=expense, income=totals.get("income", 0), count=count, by_source=by_source,
        by_pay=[dict(r) for r in by_pay],
        categories=[{"id": r["id"], "name": r["name"], "icon": r["icon"], "budget": r["budget"],
                     "amount": r["amount"], "count": r["n"],
                     "pct": (r["amount"] / expense * 100) if expense else 0,
                     "prev": prev.get(r["id"], 0)} for r in by_cat],
        alerts=budget_alerts, recent=[dict(r) for r in recent], trend=list(reversed(trend)))


# ---------------------------------------------------------------- 🐷 piggy bank

@app.get("/api/piggy")
def piggy_list():
    with conn() as c:
        piggy.record_due(c)
        return jsonify(piggy.listing(c))


@app.post("/api/piggy/<month>/refresh")
def piggy_refresh(month):
    with conn() as c:
        if not piggy.refresh(c, month):
            abort(404)
        return jsonify(piggy.listing(c))


# ---------------------------------------------------------------- import: Gmail & screenshots

@app.post("/api/gmail/accounts")
def gmail_add():
    data = request.get_json()
    try:
        with conn() as c:
            gmail_sync.add_account(c, data.get("address", ""), data.get("password", ""))
    except gmail_sync.SyncError as e:
        return jsonify(error=str(e)), 400
    return jsonify(ok=True)


@app.delete("/api/gmail/accounts")
def gmail_remove():
    with conn() as c:
        gmail_sync.remove_account(c, request.args["address"])
    return jsonify(ok=True)


@app.post("/api/gmail/sync")
def gmail_sync_route():
    try:
        with conn() as c:
            r = gmail_sync.sync(c)
            if r.get("imported"):
                notifications.add(c, "gmail", "✉️", f"{r['imported']} đơn mới từ Gmail", link={"tab": "tx"})
            return jsonify(r)
    except gmail_sync.SyncError as e:
        return jsonify(error=str(e)), 400


@app.post("/api/gmail/reparse")
def gmail_reparse():
    with conn() as c:
        return jsonify(gmail_sync.reparse(c))


@app.get("/api/emails")
def list_emails():
    status = request.args.get("status", "no_amount")
    with conn() as c:
        rows = c.execute("SELECT message_id, received, sender, subject, status, substr(body, 1, 3000) AS body "
                         "FROM emails WHERE status = ? ORDER BY received DESC LIMIT 100", (status,)).fetchall()
    return jsonify([dict(r) for r in rows])


@app.delete("/api/emails")
def dismiss_email():
    with conn() as c:
        c.execute("UPDATE emails SET status = 'dismissed' WHERE message_id = ?", (request.args["id"],))
    return jsonify(ok=True)


# ---------------------------------------------------------------- import: iPhone via Google Sheet

@app.post("/api/phone/connect")
def phone_connect():
    try:
        with conn() as c:
            return jsonify(ok=True, sheet=phone_inbox.connect(c, (request.get_json() or {}).get("code", "")))
    except phone_inbox.InboxError as e:
        return jsonify(error=str(e)), 400


@app.delete("/api/phone")
def phone_disconnect():
    with conn() as c:
        phone_inbox.disconnect(c)
    return jsonify(ok=True)


@app.get("/api/phone/code")
def phone_code():
    try:
        with conn() as c:
            return jsonify(code=phone_inbox.code(c))
    except phone_inbox.InboxError as e:
        return jsonify(error=str(e)), 400


@app.get("/api/phone/script")
def phone_script():
    return send_from_directory(RESOURCES / "phone", "Code.gs", mimetype="text/plain")


@app.post("/api/phone/sync")
def phone_sync():
    try:
        with conn() as c:
            r = phone_inbox.sync(c)
            if r["imported"]:
                notifications.add(c, "phone", "📱", f"Đã lấy {r['imported']} khoản mới từ iPhone",
                                  link={"tab": "tx", "src": "phone"})
            return jsonify(r)
    except phone_inbox.InboxError as e:
        return jsonify(error=str(e)), 400


@app.post("/api/phone/push")
def phone_push():
    try:
        with conn() as c:
            return jsonify(phone_inbox.push(c))
    except phone_inbox.InboxError as e:
        return jsonify(error=str(e)), 400


# Every change is mirrored to the Sheet a few seconds later, batched so a burst of edits makes one upload.
PUSH_DELAY = 10
WRITES = ("/api/transactions", "/api/categories", "/api/rules", "/api/gmail/sync", "/api/gmail/reparse",
          "/api/statements", "/api/statement-lines", "/api/phone/sync", "/api/piggy")
_push_timer: threading.Timer | None = None
_push_lock = threading.Lock()


def _push_now():
    try:
        with conn() as c:
            if phone_inbox.push_enabled(c):
                phone_inbox.push(c)
    except Exception as e:  # noqa: BLE001 — a background upload must never take the app down; the error is shown in Cài đặt
        print(f"push to Sheet failed: {e}", file=sys.stderr)


def schedule_push(delay: float | None = None) -> None:
    global _push_timer
    with _push_lock:
        if _push_timer:
            _push_timer.cancel()
        _push_timer = threading.Timer(PUSH_DELAY if delay is None else delay, _push_now)
        _push_timer.daemon = True
        _push_timer.start()


@app.after_request
def push_after_write(resp):
    if request.method != "GET" and resp.status_code < 400 and request.path.startswith(WRITES):
        with conn() as c:
            if phone_inbox.push_enabled(c):
                schedule_push()
    return resp


_alert_lock = threading.Lock()  # two writes finishing together must not both send the same notification


@app.after_request
def alert_after_write(resp):
    if request.method != "GET" and resp.status_code < 400 and request.path.startswith(WRITES):
        try:
            with _alert_lock, conn() as c:
                alerts.notify_crossings(c, desktop=app.config["DESKTOP"])
        except Exception as e:  # noqa: BLE001 — a notification must never fail the write it follows
            print(f"budget alert failed: {e}", file=sys.stderr)
    return resp


# ---------------------------------------------------------------- statements & reconciliation

@app.get("/api/accounts")
def list_accounts():
    with conn() as c:
        rows = c.execute("SELECT pay_account FROM transactions WHERE pay_account IS NOT NULL "
                         "UNION SELECT account FROM statements ORDER BY 1").fetchall()
    return jsonify([r[0] for r in rows])


@app.post("/api/statements")
def import_statement():
    import hashlib
    f = request.files.get("file")
    account = (request.form.get("account") or "").strip()
    if not f or not account:
        return jsonify(error="Chọn file sao kê và nhập tên thẻ/tài khoản (ví dụ: Visa Techcombank)."), 400
    data = f.read()
    try:
        lines = statements.parse_file(f.filename or "", data, request.form.get("password", ""))
    except statements.NeedPassword as e:
        return jsonify(error=str(e), need_password=True), 400
    except statements.StatementError as e:
        return jsonify(error=str(e)), 400
    sha = hashlib.sha256(data).hexdigest()
    with conn() as c:
        old = c.execute("SELECT id FROM statements WHERE file_sha = ?", (sha,)).fetchone()
        if old:
            return jsonify(error="File sao kê này đã được nhập rồi.", id=old["id"]), 409
        sid = c.execute("INSERT INTO statements(account, filename, file_sha) VALUES (?, ?, ?)",
                        (account, f.filename, sha)).lastrowid
        c.executemany("INSERT INTO statement_lines(statement_id, date, amount, kind, description, status) "
                      "VALUES (?, ?, ?, ?, ?, ?)",
                      [(sid, l["date"], l["amount"], l["kind"], l["description"], "ignored" if l["ignored"] else None)
                       for l in lines])
        return jsonify(reconcile.run(c, sid))


@app.get("/api/statements")
def list_statements():
    with conn() as c:
        rows = c.execute("SELECT s.*, MIN(l.date) AS first, MAX(l.date) AS last, COUNT(l.id) AS lines "
                         "FROM statements s LEFT JOIN statement_lines l ON l.statement_id = s.id "
                         "GROUP BY s.id ORDER BY last DESC, s.id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/statements/<int:sid>")
def get_statement(sid):
    with conn() as c:
        try:
            return jsonify(reconcile.run(c, sid))
        except KeyError:
            abort(404)


@app.delete("/api/statements/<int:sid>")
def delete_statement(sid):
    with conn() as c:
        c.execute("DELETE FROM statements WHERE id = ?", (sid,))  # transactions added from it stay
    return jsonify(ok=True)


@app.get("/api/statement-lines/<int:lid>/candidates")
def line_candidates(lid):
    with conn() as c:
        ln = c.execute("SELECT * FROM statement_lines WHERE id = ?", (lid,)).fetchone()
        rows = c.execute(
            "SELECT t.*, c.icon AS icon, c.name AS category FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
            "WHERE t.status = 'ok' AND t.kind = ? AND t.date BETWEEN date(?, '-7 days') AND date(?, '+7 days') "
            "AND t.id NOT IN (SELECT match_tx_id FROM statement_lines WHERE match_tx_id IS NOT NULL AND id != ?) "
            "ORDER BY abs(t.amount - ?), abs(julianday(t.date) - julianday(?)) LIMIT 20",
            (ln["kind"], ln["date"], ln["date"], lid, ln["amount"], ln["date"])).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/statement-lines/<int:lid>/<action>")
def line_action(lid, action):
    data = request.get_json(silent=True) or {}
    with conn() as c:
        ln = c.execute("SELECT l.*, s.account FROM statement_lines l JOIN statements s ON s.id = l.statement_id "
                       "WHERE l.id = ?", (lid,)).fetchone()
        if not ln:
            abort(404)
        if action == "add":  # a card charge nobody recorded
            tid = _insert(c, {"date": ln["date"], "amount": ln["amount"], "kind": ln["kind"],
                              "description": ln["description"], "source": "statement", "pay_account": ln["account"]})
            c.execute("UPDATE statement_lines SET status = 'added', match_tx_id = ? WHERE id = ?", (tid, lid))
        elif action == "link":
            tid = int(data["tx_id"])
            c.execute("UPDATE statement_lines SET status = 'manual', match_tx_id = ? WHERE id = ?", (tid, lid))
            if data.get("use_statement_amount"):  # the receipt amount was typed wrong (tip, FX fee…)
                c.execute("UPDATE transactions SET amount = ? WHERE id = ?", (ln["amount"], tid))
            c.execute("UPDATE transactions SET pay_account = COALESCE(pay_account, ?) WHERE id = ?", (ln["account"], tid))
        elif action == "unlink":
            if ln["status"] == "added":  # undo "add": the transaction only existed because of this line
                c.execute("DELETE FROM transactions WHERE id = ? AND source = 'statement'", (ln["match_tx_id"],))
            c.execute("UPDATE statement_lines SET status = NULL, match_tx_id = NULL WHERE id = ?", (lid,))
        elif action == "ignore":
            c.execute("UPDATE statement_lines SET status = 'ignored', match_tx_id = NULL WHERE id = ?", (lid,))
        elif action == "unignore":
            c.execute("UPDATE statement_lines SET status = NULL WHERE id = ?", (lid,))
        else:
            abort(404)
        return jsonify(reconcile.run(c, ln["statement_id"]))


@app.post("/api/screenshot")
def screenshot():
    import ocr  # imported lazily: pyobjc loads slowly and only this route needs it

    results = []
    with conn() as c:
        compiled = rules.load(c)
        for f in request.files.getlist("files"):
            suffix = Path(f.filename or "x.png").suffix or ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
                f.save(tmp.name)
                try:
                    rows = ocr.ocr_rows(tmp.name)
                except RuntimeError as e:
                    results.append({"file": f.filename, "error": str(e), "candidates": [], "text": ""})
                    continue
            cands = parsers.parse_ocr_rows(rows)
            for cand in cands:
                cand["category_id"] = rules.categorize(c, cand["description"], "expense", compiled)
                # Overlapping history screenshots show the same payments again: offer them unticked.
                if c.execute("SELECT 1 FROM transactions WHERE status = 'ok' AND kind = 'expense' AND amount = ? "
                             "AND abs(julianday(date) - julianday(?)) <= 1", (cand["amount"], cand["date"])).fetchone():
                    cand["selected"], cand["duplicate"] = False, True
            results.append({"file": f.filename, "candidates": cands, "text": "\n".join(rows)})
    return jsonify(results)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    db.init()
    app.run(host="127.0.0.1", port=args.port, threaded=True)
