"""iPhone → Google Sheet → app. The Apps Script side is tested in test_apps_script.py; here it is faked."""
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
