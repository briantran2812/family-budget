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

import db
import gmail_sync
import parsers
import rules

VERSION = "1.2.0"
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
                       gmail_accounts=gmail_sync.accounts(c),
                       gmail_query=db.get_setting(c, "gmail_query", gmail_sync.DEFAULT_QUERY),
                       gmail_last_sync=db.get_setting(c, "gmail_last_sync"))


@app.post("/api/profile")
def profile():
    data = request.get_json()
    with conn() as c:
        for key in ("user_name", "onboarded", "gmail_query"):
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
        "INSERT INTO transactions(date, amount, kind, description, source, category_id) VALUES (?, ?, ?, ?, ?, ?)",
        (t.get("date") or date.today().isoformat(), amount, kind, (t.get("description") or "").strip(),
         t.get("source", "manual"), cid)).lastrowid


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


@app.patch("/api/transactions/<int:tid>")
def update_transaction(tid):
    data = request.get_json()
    allowed = {k: data[k] for k in ("date", "amount", "kind", "description", "category_id", "status") if k in data}
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
    expense = totals.get("expense", 0)
    return jsonify(
        month=month, expense=expense, income=totals.get("income", 0), count=count, by_source=by_source,
        categories=[{"id": r["id"], "name": r["name"], "icon": r["icon"], "budget": r["budget"],
                     "amount": r["amount"], "count": r["n"],
                     "pct": (r["amount"] / expense * 100) if expense else 0,
                     "prev": prev.get(r["id"], 0)} for r in by_cat],
        recent=[dict(r) for r in recent], trend=list(reversed(trend)))


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
            return jsonify(gmail_sync.sync(c))
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
            results.append({"file": f.filename, "candidates": cands, "text": "\n".join(rows)})
    return jsonify(results)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    db.init()
    app.run(host="127.0.0.1", port=args.port, threaded=True)
