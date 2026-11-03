"""Gmail via the sheet's "Email" tab (Code.gs SCRIPT_VERSION 3). The Apps Script side is in tests/apps_script/harness.mjs."""
import db
import gmail_sync
import parsers
import phone_inbox
import sheet_email
from samples import shopee_email, tiktok_email

CODE = "https://script.google.com/macros/s/AKfyc-test_1/exec?k=0123456789abcdef01234567"  # = conftest.PHONE_CODE
SHOPEE = "Shopee <info@mail.shopee.vn>"


def mail(gid, subject, body, date="2026-11-01T09:00:00", sender=SHOPEE, note="", mid=""):
    """One row as Code.gs emails_() returns it; `body` is already text (Code.gs ports parsers.html_to_text)."""
    return {"id": gid, "date": date, "from": sender, "subject": subject, "body": body, "note": note, "mid": mid, "row": 2}


def shopee(gid, oid, price, date="2026-11-01T09:00:00", subject=None, item="Kem chống nắng Anessa", mid=""):
    body = parsers.html_to_text(shopee_email(oid, [(item, 1, price)], 0, 0))
    return mail(gid, subject or f"Xác nhận đơn hàng #{oid}", body, date, mid=mid)


def connect_v3(conn, fake_sheet):
    fake_sheet["version"] = sheet_email.EMAIL_SCRIPT_VERSION
    phone_inbox.connect(conn, CODE)


def email_calls(fake_sheet):
    return [c[2] for c in fake_sheet["calls"] if c[1] == "emails"]


def test_old_script_is_never_asked_for_emails(conn, fake_sheet):
    fake_sheet["emails"] = [shopee("g1", "261101AAAA1111", 465_000)]
    phone_inbox.connect(conn, CODE)  # the fixture's script is version 2, like the one in production
    r = phone_inbox.sync(conn)
    assert r["emails_imported"] == 0 and "emails" not in r and "emails_error" not in r
    assert email_calls(fake_sheet) == []
    assert not sheet_email.available(conn)
    fake_sheet["version"] = 3  # Code.gs promoted: the same sync that learns the version pulls emails
    assert phone_inbox.sync(conn)["emails_imported"] == 1


def test_shopee_email_becomes_a_transaction_with_amount_and_item(conn, fake_sheet):
    connect_v3(conn, fake_sheet)
    fake_sheet["emails"] = [shopee("g1", "261101AAAA1111", 465_000, item="Son kem lì Romand")]
    r = phone_inbox.sync(conn)
    assert (r["emails_imported"], r["emails"]["found"], r["emails"]["new"]) == (1, 1, 1)
    t = conn.execute("SELECT date, amount, source, order_id, description FROM transactions").fetchone()
    assert tuple(t) == ("2026-11-01", 465_000, "shopee", "261101AAAA1111", "Son kem lì Romand")
    e = conn.execute("SELECT message_id, status, sender FROM emails").fetchone()
    assert tuple(e) == ("sheet:g1", "imported", SHOPEE)


def test_cursor_and_pages(conn, fake_sheet):
    connect_v3(conn, fake_sheet)
    fake_sheet["email_page"] = 2
    fake_sheet["emails"] = [shopee(f"g{i}", f"2611010000{i:04d}", 100_000 + i * 1000) for i in range(5)]
    assert phone_inbox.sync(conn)["emails_imported"] == 5
    assert [c.get("since") for c in email_calls(fake_sheet)] == ["", "g1", "g3"]
    assert db.get_setting(conn, "sheet_email_cursor") == "g4"
    fake_sheet["calls"].clear()
    fake_sheet["emails"].append(shopee("g5", "261101AAAA5555", 50_000))
    r = phone_inbox.sync(conn)
    assert r["emails_imported"] == 1 and r["emails"]["found"] == 1
    assert [c.get("since") for c in email_calls(fake_sheet)] == ["g4"]


def test_unknown_cursor_starts_over_without_duplicates(conn, fake_sheet):
    """The script deleted the cursor's row (older than 90 days): it sends the tab again from the top."""
    connect_v3(conn, fake_sheet)
    fake_sheet["emails"] = [shopee("g1", "261101AAAA1111", 465_000)]
    phone_inbox.sync(conn)
    db.set_setting(conn, "sheet_email_cursor", "pruned")
    r = phone_inbox.sync(conn)
    assert (r["emails_imported"], r["emails"]["found"], r["emails"]["new"]) == (0, 1, 0)
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_same_order_by_imap_and_by_sheet_counts_once(conn, fake_sheet, monkeypatch):
    connect_v3(conn, fake_sheet)
    db.set_setting(conn, "gmail_accounts", '["lan@gmail.com"]')
    body = parsers.html_to_text(shopee_email("261102BBBB2222", [("Nước giặt Omo", 1, 219_000)], 0, 0))
    monkeypatch.setattr(gmail_sync, "_fetch_new", lambda c, a, q: (1, [
        ("2026-11-02T08:00:00", "<abc@mail.shopee.vn>", SHOPEE, "Xác nhận đơn hàng #261102BBBB2222", body)]))
    assert gmail_sync.sync(conn)["imported"] == 1
    fake_sheet["emails"] = [shopee("g9", "261102BBBB2222", 219_000, "2026-11-02T08:00:00", item="Nước giặt Omo")]
    r = phone_inbox.sync(conn)
    assert (r["emails_imported"], r["emails"]["duplicate"]) == (0, 1)
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
    assert {r[0] for r in conn.execute("SELECT message_id FROM emails")} == {"<abc@mail.shopee.vn>", "sheet:g9"}


def test_email_without_order_number_counts_once_via_its_message_id(conn, fake_sheet, monkeypatch):
    """No order number: the order id is a hash of the RFC Message-ID, which the sheet row carries too."""
    connect_v3(conn, fake_sheet)
    db.set_setting(conn, "gmail_accounts", '["lan@gmail.com"]')
    body = "Cảm ơn bạn đã mua hàng\nTổng thanh toán: 150.000đ"
    monkeypatch.setattr(gmail_sync, "_fetch_new", lambda c, a, q: (1, [
        ("2026-11-02T08:00:00", "<n0@tiktok>", "TikTok Shop <no-reply@tiktok.com>", "Xác nhận thanh toán", body)]))
    gmail_sync.sync(conn)
    fake_sheet["emails"] = [mail("g7", "Xác nhận thanh toán", body, sender="TikTok Shop <no-reply@tiktok.com>",
                                 mid="<n0@tiktok>")]
    assert phone_inbox.sync(conn)["emails"]["duplicate"] == 1
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_promotions_are_skipped_and_cancellation_applied(conn, fake_sheet):
    connect_v3(conn, fake_sheet)
    tiktok = parsers.html_to_text(tiktok_email("577001234567890123", [("Tai nghe bluetooth Soundpeats", 1, 459_000)]))
    fake_sheet["emails"] = [
        mail("p1", "Siêu sale 11.11 — voucher 50%", "₫99.000", "2026-11-01T07:00:00"),
        mail("t2", "Đơn hàng #261103CCCC3333 đã bị hủy", "Mã đơn hàng: 261103CCCC3333", "2026-11-03T10:00:00"),
        shopee("t1", "261103CCCC3333", 200_000, "2026-11-03T08:00:00"),  # listed after its cancellation; applied first
        mail("k1", "Xác nhận đơn hàng TikTok Shop", tiktok, "2026-11-02T08:00:00", sender="TikTok Shop <no-reply@tiktok.com>"),
    ]
    r = phone_inbox.sync(conn)["emails"]
    assert (r["imported"], r["cancelled"], r["skipped"]) == (2, 1, 1)
    rows = dict(conn.execute("SELECT order_id, status FROM transactions"))
    assert rows == {"261103CCCC3333": "cancelled", "577001234567890123": "ok"}
    assert conn.execute("SELECT amount FROM transactions WHERE source = 'tiktok'").fetchone()[0] == 459_000
    assert conn.execute("SELECT body FROM emails WHERE message_id = 'sheet:p1'").fetchone()[0] == ""


def test_hand_forwarded_email_is_credited_to_the_shop(conn, fake_sheet):
    connect_v3(conn, fake_sheet)
    body = ("---------- Forwarded message ---------\nFrom: Shopee <info@mail.shopee.vn>\nDate: 1 Nov 2026\n" +
            parsers.html_to_text(shopee_email("261101DDDD4444", [("Bỉm Bobby", 1, 345_000)], 0, 0)))
    fake_sheet["emails"] = [mail("f1", "Fwd: Xác nhận đơn hàng #261101DDDD4444", body, sender="Lan <lan@gmail.com>",
                                 note="chuyển tiếp")]
    phone_inbox.sync(conn)
    assert tuple(conn.execute("SELECT source, amount FROM transactions").fetchone()) == ("shopee", 345_000)


def test_email_error_does_not_break_the_iphone_sync(conn, fake_sheet):
    connect_v3(conn, fake_sheet)
    fake_sheet["rows"] = [{"id": "a1", "time": "2026-11-02T12:30:00", "amount": 45000, "description": "Phở", "row": 2}]
    fake_sheet["email_error"] = "Apps Script báo lỗi: Exception: Gmail quota"
    r = phone_inbox.sync(conn)
    assert r["imported"] == 1 and r["emails_imported"] == 0 and "Gmail quota" in r["emails_error"]
    assert "Gmail quota" in sheet_email.status(conn)["sheet_email_error"]
    fake_sheet["email_error"] = None
    phone_inbox.sync(conn)
    assert sheet_email.status(conn)["sheet_email_error"] == ""


def test_disconnect_forgets_the_cursor(conn, fake_sheet):
    connect_v3(conn, fake_sheet)
    fake_sheet["emails"] = [shopee("g1", "261101AAAA1111", 465_000)]
    phone_inbox.sync(conn)
    phone_inbox.disconnect(conn)
    assert db.get_setting(conn, "sheet_email_cursor") == ""
    assert not sheet_email.available(conn)
    assert sheet_email.status(conn)["sheet_email_count"] == 1  # the emails and their transactions stay


def test_route_reports_and_rings_the_bell(api, fake_sheet):
    fake_sheet["version"] = 3
    api.post("/api/phone/connect", json={"code": CODE})
    fake_sheet["emails"] = [shopee("g1", "261101AAAA1111", 465_000)]
    fake_sheet["scanned"] = "2026-11-01T09:30:00"
    assert api.post("/api/phone/sync").get_json()["emails_imported"] == 1
    bell = api.get("/api/notifications").get_json()["items"]
    assert any(n["title"] == "1 đơn mới từ Gmail (qua Google Sheet)" for n in bell)
    info = api.get("/api/info").get_json()
    assert info["sheet_email_available"] and info["sheet_email_count"] == 1
    assert (info["sheet_email_last_date"], info["sheet_email_scanned"]) == ("2026-11-01", "2026-11-01T09:30:00")
    assert info["sheet_email_required"] == 3 and info["sheet_email_last_pull"]
    assert not info["phone_script_outdated"]


def test_authorization_page_is_explained():
    hint = phone_inbox._explain_html("<html><body>Authorization is required to perform that action.</body></html>",
                                     "https://script.google.com/x")
    assert "batQuetEmail" in hint and "New version" in hint
