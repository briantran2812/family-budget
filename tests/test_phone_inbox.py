"""iPhone → Google Sheet → app. The Apps Script side is tested in test_apps_script.py; here it is faked."""
import json

import pytest

import phone_inbox

CODE = "https://script.google.com/macros/s/AKfyc-test_1/exec?k=0123456789abcdef01234567"  # = conftest.PHONE_CODE


def row(rid, amount, desc="Phở bò", time="2026-11-02T12:30:00", account="Tiền mặt", n=2):
    return {"id": rid, "time": time, "amount": amount, "description": desc, "account": account, "by": "iPhone", "row": n}


def test_connect_validates_format_before_calling_google(conn, fake_sheet):
    with pytest.raises(phone_inbox.InboxError, match="Mã kết nối có dạng"):
        phone_inbox.connect(conn, "https://evil.example.com/exec?k=0123456789abcdef")
    assert fake_sheet["calls"] == []


def test_connect_stores_code_in_keychain_not_db(conn, fake_sheet, fake_keyring):
    assert phone_inbox.connect(conn, "  " + CODE + "\n") == "https://docs.google.com/spreadsheets/d/abc"
    assert fake_keyring[(phone_inbox.KEYRING_SERVICE, phone_inbox.KEYRING_USER)] == CODE
    assert phone_inbox.connected(conn)
    assert CODE not in str([tuple(r) for r in conn.execute("SELECT * FROM settings")])
    assert phone_inbox.code(conn) == CODE


def test_connect_wrong_secret_keeps_nothing(conn, fake_sheet, fake_keyring):
    with pytest.raises(phone_inbox.InboxError, match="Mã kết nối sai"):
        phone_inbox.connect(conn, CODE.replace("0123", "9999"))
    assert not phone_inbox.connected(conn) and not fake_keyring


def test_sync_imports_categorises_and_dedups(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [row("a1", 45000), row("a2", 1500000, "Học phí tháng 11", account="Chuyển khoản", n=3)]
    r = phone_inbox.sync(conn)
    assert (r["total"], r["imported"], r["duplicate"], r["invalid"]) == (2, 2, 0, 0)
    txs = conn.execute("SELECT t.*, c.name AS cat FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
                       "ORDER BY t.amount").fetchall()
    assert [(t["date"], t["amount"], t["source"], t["pay_account"]) for t in txs] == [
        ("2026-11-02", 45000, "phone", "Tiền mặt"), ("2026-11-02", 1500000, "phone", "Chuyển khoản")]
    assert txs[1]["cat"] == "Học phí"
    again = phone_inbox.sync(conn)
    assert (again["imported"], again["duplicate"]) == (0, 2)
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2


def test_sync_skips_unreadable_rows_and_reports_them(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [row("b1", None, n=4), row("b2", 0, n=5), row("", 5000, n=6), row("b3", 5000, time="?", n=7),
                     row("b4", 30000, n=8)]
    r = phone_inbox.sync(conn)
    assert (r["imported"], r["invalid"], r["bad_rows"]) == (1, 4, [4, 5, 6, 7])


def test_sync_enriches_a_transaction_added_from_a_statement(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    conn.execute("INSERT INTO transactions(date, amount, description, source, pay_account) "
                 "VALUES ('2026-11-03', 250000, 'POS 1234 HIGHLANDS', 'statement', 'Visa Techcombank')")
    fake_sheet["rows"] = [row("c1", 250000, "Cà phê với khách", account="Visa")]
    assert phone_inbox.sync(conn)["imported"] == 1
    t = conn.execute("SELECT * FROM transactions").fetchall()
    assert len(t) == 1
    assert (t[0]["source"], t[0]["description"], t[0]["pay_account"]) == ("phone", "Cà phê với khách", "Visa Techcombank")


def test_sync_without_connection(conn, fake_sheet):
    with pytest.raises(phone_inbox.InboxError, match="Chưa kết nối"):
        phone_inbox.sync(conn)


def test_disconnect_forgets_code(conn, fake_sheet, fake_keyring):
    phone_inbox.connect(conn, CODE)
    phone_inbox.disconnect(conn)
    assert not phone_inbox.connected(conn) and not fake_keyring


def test_api_routes(api, fake_sheet):
    assert api.post("/api/phone/connect", json={"code": "nope"}).status_code == 400
    assert api.post("/api/phone/connect", json={"code": CODE}).get_json()["ok"]
    info = api.get("/api/info").get_json()
    assert info["phone_connected"] and info["phone_sheet_url"].endswith("/abc")
    fake_sheet["rows"] = [row("d1", 45000)]
    assert api.post("/api/phone/sync").get_json()["imported"] == 1
    assert api.get("/api/phone/code").get_json()["code"] == CODE
    assert "function doGet" in api.get("/api/phone/script").get_data(as_text=True)
    assert api.delete("/api/phone").status_code == 200
    assert api.post("/api/phone/sync").status_code == 400


def test_real_http_follows_google_redirect(monkeypatch):
    """_get against a local server that answers like Apps Script: 302 to another host, then JSON."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/macros/"):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{srv.server_port}/echo?{self.path.split('?', 1)[1]}")
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "query": self.path}).encode())

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        data = phone_inbox._get(f"http://127.0.0.1:{srv.server_port}/macros/s/x/exec?k=abc", "list")
    finally:
        srv.shutdown()
    assert data["query"] == "/echo?k=abc&a=list"


@pytest.mark.parametrize("pasted, hint", [
    ("https://script.google.com/u/1/home/projects/1eAol2W03mg3Q0unkJ5OD7Er5k97TcVTJw/edit", "trang soạn code"),
    ("https://script.google.com/macros/s/AKfyc-test_1/exec", "Thiếu phần"),
])
def test_connect_explains_common_paste_mistakes(conn, fake_sheet, pasted, hint):
    with pytest.raises(phone_inbox.InboxError, match=hint):
        phone_inbox.connect(conn, pasted)


def test_workspace_and_multi_account_urls_are_accepted():
    k = "?k=0123456789abcdef01234567"
    for url in ("https://script.google.com/a/macros/example.com/s/AKfy_x-1/exec",
                "https://script.google.com/macros/u/1/s/AKfy_x-1/exec"):
        assert phone_inbox.CODE_RE.match(url + k), url


@pytest.mark.parametrize("body, url, hint", [
    ("<html>Sign in</html>", "https://accounts.google.com/v3/signin/identifier?continue=x", "đòi đăng nhập"),
    ("<html><body><div>Script function not found: doGet</div></body></html>", "https://script.google.com/x", "New version"),
    ("<html><style>p{}</style><body><p>TypeError: Cannot read properties of null</p></body></html>",
     "https://script.google.com/x", "TypeError: Cannot read properties of null"),
])
def test_html_reply_is_explained(body, url, hint):
    assert hint in phone_inbox._explain_html(body, url)



# ---------------------------------------------------------------- mirror to the Sheet

def test_mirror_payload_rows_and_monthly_summary(conn, fake_sheet):
    import db
    db.set_setting(conn, "device_name", "MacBook Lan")
    cat = lambda name: conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()[0]
    conn.executemany("INSERT INTO transactions(date, amount, kind, description, source, category_id, pay_account, status) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        ("2026-11-02", 45_000, "expense", "Phở", "phone", cat("Ăn uống & đi chợ"), "Tiền mặt", "ok"),
        ("2026-11-01", 86_000, "expense", "Highlands", "screenshot", cat("Ăn uống & đi chợ"), "Ví MoMo", "ok"),
        ("2026-11-01", 50_000_000, "income", "Lương", "manual", cat("Lương"), None, "ok"),
        ("2026-11-01", 99_000, "expense", "Đơn huỷ", "shopee", None, None, "cancelled"),
        ("2026-10-20", 465_000, "expense", "Kem", "shopee", None, None, "ok")])
    p = phone_inbox.mirror_payload(conn)
    assert p["device"] == "MacBook Lan" and len(p["rows"]) == 5
    assert p["rows"][0][:9] == ["2026-11-02", "Chi", 45_000, "Phở", "Ăn uống & đi chợ", "Tiền mặt", "iPhone", "Có", "MacBook Lan"]
    assert [r for r in p["rows"] if r[3] == "Đơn huỷ"][0][7] == "Không"
    nov = {(r[2], r[3]): (r[4], r[5]) for r in p["summary"] if r[1] == "2026-11"}
    assert nov[("Tổng", "Tổng chi")] == (131_000, 1.0)           # the cancelled order is not counted
    assert nov[("Tổng", "Còn lại")] == (50_000_000 - 131_000, "")
    assert nov[("Hạng mục", "Ăn uống & đi chợ")] == (131_000, 1.0)
    assert nov[("Cách trả", "Ví MoMo")] == (86_000, round(86_000 / 131_000, 4))
    assert {r[1] for r in p["summary"] if r[2] not in ("Hoạt động", "Lỗi")} == {"2026-11", "2026-10"}  # usage: this month
    assert not [r for r in p["summary"] if r[2] == "Ống heo"]
    conn.execute("INSERT INTO piggy(month, income, expense, saved) VALUES ('2026-10', 0, 465000, -465000)")
    piggy_rows = [r for r in phone_inbox.mirror_payload(conn)["summary"] if r[2] == "Ống heo"]
    assert piggy_rows == [["MacBook Lan", "2026-10", "Ống heo", "Bỏ ống heo", -465_000, ""]]


def test_push_records_time_and_error(conn, fake_sheet):
    import db
    phone_inbox.connect(conn, CODE)
    assert phone_inbox.push(conn)["ok"]
    assert db.get_setting(conn, "phone_last_push") and not db.get_setting(conn, "phone_push_error")
    keyring_code = phone_inbox.code(conn)
    phone_inbox.keyring.set_password(phone_inbox.KEYRING_SERVICE, phone_inbox.KEYRING_USER, keyring_code + "0")
    with pytest.raises(phone_inbox.InboxError):
        phone_inbox.push(conn)
    assert "Mã kết nối sai" in db.get_setting(conn, "phone_push_error")


def test_writes_schedule_a_push_only_when_enabled(api, fake_sheet):
    api.post("/api/transactions", json={"amount": 45_000, "description": "Phở"})
    assert fake_sheet["scheduled"] == []                          # not connected
    api.post("/api/phone/connect", json={"code": CODE})
    api.post("/api/transactions", json={"amount": 45_000, "description": "Phở"})
    api.post("/api/phone/sync")
    assert len(fake_sheet["scheduled"]) == 2
    api.post("/api/profile", json={"phone_push": "0"})
    api.post("/api/transactions", json={"amount": 45_000, "description": "Phở"})
    assert len(fake_sheet["scheduled"]) == 2
    assert api.get("/api/info").get_json()["phone_push"] is False


def test_push_route(api, fake_sheet):
    api.post("/api/phone/connect", json={"code": CODE})
    api.post("/api/profile", json={"device_name": "MacBook Lan"})
    api.post("/api/transactions", json={"amount": 45_000, "description": "Phở", "date": "2026-11-02"})
    r = api.post("/api/phone/push").get_json()
    assert r["rows"] == 1 and fake_sheet["pushes"][-1]["device"] == "MacBook Lan"
    assert api.get("/api/info").get_json()["phone_last_push"]


def test_real_http_post_follows_google_redirect():
    """doPost runs on the POST; Google then answers 302 and the client must fetch the result with a GET."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{srv.server_port}/echo")
            self.end_headers()

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true, "rows": 1}')

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = phone_inbox._post(f"http://127.0.0.1:{srv.server_port}/macros/s/x/exec?k=abc", {"a": "mirror", "d": "Phở"})
    finally:
        srv.shutdown()
    assert r == {"ok": True, "rows": 1} and seen["body"] == {"a": "mirror", "d": "Phở"}



def test_category_picked_on_the_phone_wins_over_keywords(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [{**row("e1", 300_000, "Quà sinh nhật bé An"), "category": "🍼 Mẹ & bé"},
                          {**row("e2", 45_000, "Phở bò"), "category": "✨ Tự động"},
                          {**row("e3", 25_000, "cà phê"), "category": ""}]
    phone_inbox.sync(conn)
    got = dict(conn.execute("SELECT t.order_id, c.name FROM transactions t LEFT JOIN categories c ON c.id = t.category_id"))
    assert got["e1"] == "Mẹ & bé"
    assert got["e2"] == "Ăn uống & đi chợ"    # not a category name: falls back to keywords ("pho bo")
    assert got["e3"] == "Ăn uống & đi chợ"



def test_income_category_records_money_in(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [{**row("f1", 2_000_000, "Bán đồ cũ", account="Chuyển khoản"), "category": "💰 Thu nhập khác"}]
    phone_inbox.sync(conn)
    t = conn.execute("SELECT t.kind, c.name FROM transactions t JOIN categories c ON c.id = t.category_id").fetchone()
    assert tuple(t) == ("income", "Thu nhập khác")


def test_environment_name_and_test_badge(api, fake_sheet):
    """The Sheet's name tells which environment this Mac is on; a TEST sheet gets a badge in the top bar."""
    fake_sheet["name"] = "Thu Chi — TEST"
    api.post("/api/phone/connect", json={"code": CODE})
    info = api.get("/api/info").get_json()
    assert (info["phone_sheet_name"], info["phone_env_test"], info["phone_script_outdated"]) == ("Thu Chi — TEST", True, False)
    fake_sheet["name"] = "Thu Chi — PRODUCTION"  # renamed in Google: picked up on the next sync
    api.post("/api/phone/sync")
    info = api.get("/api/info").get_json()
    assert (info["phone_sheet_name"], info["phone_env_test"]) == ("Thu Chi — PRODUCTION", False)
    api.delete("/api/phone")
    info = api.get("/api/info").get_json()
    assert (info["phone_sheet_name"], info["phone_env_test"], info["phone_script_outdated"]) == ("", False, False)


def test_old_code_gs_is_flagged_until_promoted(api, fake_sheet):
    """A script from before SCRIPT_VERSION sends no name or version: connect works, the app warns."""
    fake_sheet["version"], fake_sheet["name"] = None, None
    assert api.post("/api/phone/connect", json={"code": CODE}).get_json()["ok"]
    info = api.get("/api/info").get_json()
    assert info["phone_script_outdated"] and info["phone_script_version"] == 1
    assert info["phone_script_required"] == phone_inbox.REQUIRED_SCRIPT_VERSION
    fake_sheet["version"] = phone_inbox.REQUIRED_SCRIPT_VERSION  # new version deployed in Apps Script
    api.post("/api/phone/sync")
    assert not api.get("/api/info").get_json()["phone_script_outdated"]



def test_vietnamese_google_error_pages_are_explained():
    assert "Code.gs trên Google là bản cũ" in phone_inbox._explain_html(
        "<html><body>Lỗi Không tìm thấy hàm tập lệnh: doPost</body></html>", "https://script.google.com/x")
    assert "New version" in phone_inbox._explain_html(
        "<div>Không tìm thấy hàm tập lệnh: doGet</div>", "https://script.google.com/x")


# ---------------------------------------------------------------- Telegram bot rows (Code.gs 4)

def tg_row(rid, amount, desc="Phở", category="🛒 Ăn uống & đi chợ", account="Tiền mặt", n=2):
    return {**row(rid, amount, desc, account=account, n=n), "by": "Telegram · Lan", "category": category, "channel": "telegram"}


def test_telegram_rows_import_with_their_own_source(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [tg_row("t1", 45_000), {**row("i1", 30_000, "Gửi xe"), "channel": "iphone"},
                          tg_row("t2", 2_000_000, "Bán đồ cũ", "💰 Thu nhập khác", "Chuyển khoản", n=4)]
    r = phone_inbox.sync(conn)
    assert (r["imported"], r["telegram"], r["cancelled"]) == (3, 2, 0)
    got = {t["order_id"]: (t["source"], t["kind"], t["cat"]) for t in conn.execute(
        "SELECT t.order_id, t.source, t.kind, c.name AS cat FROM transactions t JOIN categories c ON c.id = t.category_id")}
    assert got == {"t1": ("telegram", "expense", "Ăn uống & đi chợ"), "i1": ("phone", "expense", "Đi lại & xăng xe"),
                   "t2": ("telegram", "income", "Thu nhập khác")}
    assert phone_inbox.SRC_LABEL["telegram"] == "Telegram"
    assert [r[6] for r in phone_inbox.mirror_payload(conn)["rows"] if r[3] == "Phở"] == ["Telegram"]


def test_telegram_row_an_older_app_imported_as_iphone_is_not_imported_again(conn, fake_sheet):
    """App 1.4.0 knows no Kênh column: it imported a bot row as source 'phone'. The new app must see it as done."""
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [{k: v for k, v in tg_row("t1", 45_000).items() if k != "channel"}]
    phone_inbox.sync(conn)
    fake_sheet["rows"] = [tg_row("t1", 45_000)]
    r = phone_inbox.sync(conn)
    assert (r["imported"], r["duplicate"]) == (0, 1)
    assert conn.execute("SELECT source FROM transactions").fetchall()[0][0] == "phone"


def test_rows_cancelled_after_import_are_marked_once(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [tg_row("t1", 45_000), row("p1", 30_000, "Gửi xe")]
    phone_inbox.sync(conn)
    fake_sheet["rows"] = [row("p1", 30_000, "Gửi xe")]  # Code.gs leaves cancelled rows out of `rows`…
    fake_sheet["cancelled"] = ["t1", "never-imported"]  # …and names them, also ones this Mac never saw
    r = phone_inbox.sync(conn)
    assert (r["imported"], r["cancelled"]) == (0, 1)
    status = lambda rid: conn.execute("SELECT status FROM transactions WHERE order_id = ?", (rid,)).fetchone()[0]
    assert (status("t1"), status("p1")) == ("cancelled", "ok")
    assert [r[7] for r in phone_inbox.mirror_payload(conn)["rows"] if r[3] == "Phở"] == ["Không"]
    conn.execute("UPDATE transactions SET status = 'ok' WHERE order_id = 't1'")  # restored by hand in the app
    assert phone_inbox.sync(conn)["cancelled"] == 0
    assert status("t1") == "ok"


def test_list_reply_from_code_gs_2_still_imports(conn, fake_sheet):
    """Code.gs stays at REQUIRED_SCRIPT_VERSION 2 for the iPhone: no `cancelled`, no `channel` is the normal case."""
    assert phone_inbox.REQUIRED_SCRIPT_VERSION == 2
    fake_sheet["version"] = 2
    phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = [row("a1", 45_000)]
    r = phone_inbox.sync(conn)
    assert (r["imported"], r["telegram"], r["cancelled"]) == (1, 0, 0)
    assert conn.execute("SELECT source FROM transactions").fetchone()[0] == "phone"


def test_mirror_payload_sends_budgets_for_the_bot(conn, fake_sheet):
    from datetime import datetime

    import db
    db.set_setting(conn, "device_name", "MacBook Lan")
    conn.execute("UPDATE categories SET budget = 2000000 WHERE name = 'Ăn uống & đi chợ'")
    conn.execute("UPDATE categories SET budget = 1500000 WHERE name = 'Học phí'")
    conn.execute("UPDATE categories SET budget = 0 WHERE name = 'Khác'")
    budgets = [r for r in phone_inbox.mirror_payload(conn)["summary"] if r[2] == "Ngân sách"]
    month = datetime.now().strftime("%Y-%m")
    assert budgets == [["MacBook Lan", month, "Ngân sách", "Học phí", 1_500_000, ""],
                       ["MacBook Lan", month, "Ngân sách", "Ăn uống & đi chợ", 2_000_000, ""]]


def test_mirror_payload_sends_keywords_for_the_bot(conn, fake_sheet):
    """Code.gs 5 categorises Telegram entries with these: every rule, both kinds, longest keyword first as rules.load."""
    conn.execute("INSERT INTO categories(name, kind, sort, icon) VALUES ('Nuôi mèo', 'expense', 99, '🐱')")
    conn.execute("INSERT INTO rules(keyword, category_id) SELECT 'pate meo', id FROM categories WHERE name = 'Nuôi mèo'")
    kws = phone_inbox.mirror_payload(conn)["rules"]
    assert ["pho bo", "Ăn uống & đi chợ", "expense", "🛒"] in kws
    assert ["luong", "Lương", "income", "💼"] in kws
    assert ["pate meo", "Nuôi mèo", "expense", "🐱"] in kws
    assert len(kws) == conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
    assert [len(k[0]) for k in kws] == sorted((len(k[0]) for k in kws), reverse=True)
    assert len(json.dumps(kws, ensure_ascii=False).encode()) < 100_000, "fits one CacheService value"


def test_sync_notification_names_telegram(api, fake_sheet):
    api.post("/api/phone/connect", json={"code": CODE})
    fake_sheet["rows"] = [tg_row("t1", 45_000)]
    assert api.post("/api/phone/sync").get_json()["telegram"] == 1
    fake_sheet["rows"] = [tg_row("t1", 45_000), row("p2", 30_000, "Gửi xe")]
    api.post("/api/phone/sync")
    titles = [n["title"] for n in api.get("/api/notifications").get_json()["items"]]
    assert "Đã lấy 1 khoản mới từ Telegram" in titles and "Đã lấy 1 khoản mới từ iPhone" in titles
