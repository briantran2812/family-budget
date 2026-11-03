import io
import sys
import types
from datetime import datetime

import db
import phone_inbox
import usage

CODE = "https://script.google.com/macros/s/AKfyc-test_1/exec?k=0123456789abcdef01234567"  # = conftest.PHONE_CODE


def activity(summary, group="Hoạt động"):
    return {r[3]: r[4] for r in summary if r[2] == group}


def test_record_counts_and_rows(conn):
    db.set_setting(conn, "theme", "light")
    for _ in range(3):
        usage.record(conn, "open", "1.5.0")
    usage.record(conn, "screenshot", "4")
    usage.record(conn, "tx_add", "screenshot:3")
    usage.record(conn, "tx_add", "manual:2")
    usage.record(conn, "phone_sync", "5")
    usage.record(conn, "phone_sync", "0")
    usage.record(conn, "gmail_sync", "1")
    usage.record(conn, "piggy_view")
    conn.execute("UPDATE usage_events SET at = datetime('now', 'localtime', '-10 days') WHERE id = 1")  # an older open
    rows = usage.rows(conn, "MacBook Lan")
    month = datetime.now().strftime("%Y-%m")
    assert all(r[0] == "MacBook Lan" and r[1] == month and r[5] == "" for r in rows)
    a = activity(rows)
    assert a["Phiên bản app"] == "1.5.0" and " lúc " in a["Mở app gần nhất"]
    assert (a["Số lần mở 7 ngày"], a["Số lần mở 30 ngày"]) == (2, 3)
    assert a["Đọc ảnh (30 ngày)"] == "1 lần · đọc được 4 dòng · lưu 3 dòng"
    assert (a["Khoản từ iPhone (30 ngày)"], a["Đơn từ Gmail (30 ngày)"], a["Nhập tay (30 ngày)"]) == (5, 1, 2)
    assert (a["Xem ống heo (30 ngày)"], a["Nhập sao kê (30 ngày)"], a["Giao diện"]) == (1, 0, "Sáng")


def test_error_messages_mask_card_and_account_numbers(conn):
    assert usage.mask("Thẻ 4111 1111 1111 1234 bị từ chối") == "Thẻ •••• •••• •••• •••• bị từ chối"
    assert usage.mask("TK 0071-0012-34567, dòng 12, mã 500") == "TK ••••-••••-•••••, dòng 12, mã 500"
    usage.record_error(conn, "statement", "Sao kê 19036012345678 không đọc được " + "x" * 300)
    (detail,) = conn.execute("SELECT detail FROM usage_events WHERE kind = 'error'").fetchone()
    assert detail.startswith("statement: Sao kê •••••••••••••• không") and len(detail) <= len("statement: ") + 200
    err = [r for r in usage.rows(conn, "M") if r[2] == "Lỗi"]
    assert err[0][3].endswith("· Sao kê") and "19036012345678" not in err[0][4]


def test_only_the_ten_newest_errors_are_sent_and_repeats_are_dropped(conn):
    for i in range(12):
        usage.record_error(conn, "gmail", f"lỗi {i}")
    usage.record_error(conn, "gmail", "lỗi 11")                       # same message within 10 minutes
    assert conn.execute("SELECT COUNT(*) FROM usage_events WHERE kind = 'error'").fetchone()[0] == 12
    err = [r[4] for r in usage.rows(conn, "M") if r[2] == "Lỗi"]
    assert err == [f"lỗi {i}" for i in range(11, 1, -1)]


def test_events_older_than_60_days_are_deleted(conn):
    conn.execute("INSERT INTO usage_events(at, kind) VALUES (datetime('now', 'localtime', '-61 days'), 'open')")
    conn.execute("INSERT INTO usage_events(at, kind) VALUES (datetime('now', 'localtime', '-59 days'), 'open')")
    usage.record(conn, "open", "1.5.0")
    assert conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0] == 2


def test_mirror_payload_with_sharing_on_and_off(conn, fake_sheet):
    db.set_setting(conn, "device_name", "MacBook Lan")
    usage.record(conn, "open", "1.5.0")
    summary = phone_inbox.mirror_payload(conn)["summary"]
    assert activity(summary)["Số lần mở 30 ngày"] == 1
    assert {r[0] for r in summary if r[2] == "Hoạt động"} == {"MacBook Lan"}
    db.set_setting(conn, "share_usage", "0")
    usage.record(conn, "open", "1.5.0")                                # off: nothing new is recorded either
    usage.record_error(conn, "gmail", "x")
    assert not [r for r in phone_inbox.mirror_payload(conn)["summary"] if r[2] in ("Hoạt động", "Lỗi")]
    assert conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0] == 1


def test_push_still_works_with_sharing_off(conn, fake_sheet):
    phone_inbox.connect(conn, CODE)
    db.set_setting(conn, "share_usage", "0")
    conn.execute("INSERT INTO transactions(date, amount, description) VALUES ('2026-11-02', 45000, 'Phở')")
    assert phone_inbox.push(conn)["ok"]
    p = fake_sheet["pushes"][-1]
    assert len(p["rows"]) == 1 and [r for r in p["summary"] if r[2] == "Tổng"]
    assert not [r for r in p["summary"] if r[2] in ("Hoạt động", "Lỗi")]


# ---------------------------------------------------------------- API

def test_open_records_and_schedules_a_push_when_connected(api, fake_sheet):
    from app import VERSION
    assert api.post("/api/usage/open").get_json() == {"ok": True}
    assert fake_sheet["scheduled"] == []                               # not connected: nothing to push
    api.post("/api/phone/connect", json={"code": CODE})
    api.post("/api/usage/open")
    assert fake_sheet["scheduled"] == [None]                           # the usual PUSH_DELAY (10 s)
    a = activity(api.get("/api/usage/preview").get_json()["rows"])
    assert a["Số lần mở 7 ngày"] == 2 and a["Phiên bản app"] == VERSION


def test_preview_and_the_share_usage_setting(api, fake_sheet):
    api.post("/api/phone/connect", json={"code": CODE})
    api.post("/api/usage/open")
    p = api.get("/api/usage/preview").get_json()
    assert p["share"] and p["connected"] and p["push"] and activity(p["rows"])
    n = len(fake_sheet["scheduled"])
    assert api.post("/api/profile", json={"share_usage": "0"}).status_code == 200
    assert len(fake_sheet["scheduled"]) == n + 1                       # the Sheet loses this Mac's rows soon
    p = api.get("/api/usage/preview").get_json()
    assert p["share"] is False and p["rows"] == []
    api.post("/api/usage/open")
    assert len(fake_sheet["scheduled"]) == n + 1
    api.post("/api/profile", json={"share_usage": "1"})
    assert api.get("/api/usage/preview").get_json()["share"] is True


def test_features_and_user_facing_errors_are_recorded(api, fake_sheet, monkeypatch):
    api.post("/api/transactions", json={"amount": 45_000, "description": "Phở"})
    api.post("/api/transactions", json=[{"amount": 1, "description": "a", "source": "screenshot"}] * 2)
    api.patch("/api/categories/1", json={"budget": 2_000_000})
    api.get("/api/piggy")
    api.get("/api/piggy")                                              # refresh of an open page: not a second view
    api.post("/api/profile", json={"theme": "dark"})
    api.post("/api/profile", json={"seen_version": "1.5.0"})
    assert api.post("/api/gmail/sync").status_code == 400              # no Gmail account
    api.post("/api/phone/connect", json={"code": "https://script.google.com/macros/s/x/exec"})
    monkeypatch.setitem(sys.modules, "ocr", types.SimpleNamespace(
        ocr_rows=lambda path: (_ for _ in ()).throw(RuntimeError("Đọc ảnh cần macOS 13 trở lên"))))
    api.post("/api/screenshot", data={"files": (io.BytesIO(b"x"), "a.png")}, content_type="multipart/form-data")
    a = activity(api.get("/api/usage/preview").get_json()["rows"])
    assert (a["Nhập tay (30 ngày)"], a["Đặt ngân sách (30 ngày)"], a["Xem ống heo (30 ngày)"]) == (1, 1, 1)
    assert a["Xem Có gì mới (30 ngày)"] == 1 and a["Giao diện"] == "Tối"
    assert a["Đọc ảnh (30 ngày)"] == "1 lần · đọc được 0 dòng · lưu 2 dòng"
    errors = {r[3].split(" · ")[-1]: r[4] for r in api.get("/api/usage/preview").get_json()["rows"] if r[2] == "Lỗi"}
    assert errors["Gmail"].startswith("Chưa kết nối tài khoản Gmail")
    assert errors["iPhone"].startswith("Thiếu phần ?k=") and errors["Đọc ảnh"].startswith("Đọc ảnh cần macOS 13")


def test_server_errors_are_recorded(api, monkeypatch):
    import piggy
    from app import app
    monkeypatch.setitem(app.config, "PROPAGATE_EXCEPTIONS", False)
    monkeypatch.setattr(piggy, "listing", lambda c: 1 / 0)
    assert api.get("/api/piggy").status_code == 500
    err = [r for r in api.get("/api/usage/preview").get_json()["rows"] if r[2] == "Lỗi"]
    assert err[0][3].endswith("· Lỗi máy chủ") and err[0][4] == "GET /api/piggy: ZeroDivisionError: division by zero"
