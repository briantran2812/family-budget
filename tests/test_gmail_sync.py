"""Sync logic with IMAP replaced by canned emails — no network."""
import pytest

import gmail_sync
import parsers
from samples import shopee_email, tiktok_email


def shopee(oid, price, stamp, subject=None, items=None):
    body = parsers.html_to_text(shopee_email(oid, items or [("Kem chống nắng Anessa", 1, price)], 0, 0))
    return (stamp, f"<{oid}-{stamp}>", "Shopee <info@mail.shopee.vn>", subject or f"Xác nhận đơn hàng #{oid}", body)


@pytest.fixture
def mailbox(monkeypatch, conn, fake_keyring):
    boxes = {}

    def fake_fetch(_conn, address, _query):
        if isinstance(boxes[address], Exception):
            raise boxes[address]
        return len(boxes[address]), boxes[address]

    monkeypatch.setattr(gmail_sync, "_fetch_new", fake_fetch)
    monkeypatch.setattr(gmail_sync, "_login", lambda a, p: type("I", (), {"logout": lambda self: None})())
    return boxes


def test_add_account_validates_input(conn, fake_keyring):
    with pytest.raises(gmail_sync.SyncError):
        gmail_sync.add_account(conn, "lan@gmail.com", "short")
    with pytest.raises(gmail_sync.SyncError):
        gmail_sync.add_account(conn, "not-an-email", "abcdefghijklmnop")


def test_add_and_remove_account(conn, mailbox):
    gmail_sync.add_account(conn, " Lan@Gmail.com ", "abcd efgh ijkl mnop")
    assert gmail_sync.accounts(conn) == ["lan@gmail.com"]
    assert mailbox is not None and gmail_sync.keyring.get_password(gmail_sync.KEYRING_SERVICE, "lan@gmail.com") == "abcdefghijklmnop"
    gmail_sync.remove_account(conn, "lan@gmail.com")
    assert gmail_sync.accounts(conn) == []


def test_sync_dedups_shipping_and_applies_cancel(conn, mailbox):
    gmail_sync.add_account(conn, "lan@gmail.com", "abcdefghijklmnop")
    mailbox["lan@gmail.com"] = [
        shopee("261001AAAA1111", 465_000, "2026-10-01T09:00:00"),
        shopee("261001AAAA1111", 465_000, "2026-10-01T15:00:00", "Đơn hàng #261001AAAA1111 đang được giao"),
        shopee("261002BBBB2222", 200_000, "2026-10-02T10:00:00"),
        ("2026-10-03T08:00:00", "<c>", "Shopee", "Đơn hàng #261002BBBB2222 đã bị hủy", "Mã đơn hàng: 261002BBBB2222"),
        ("2026-10-03T09:00:00", "<p>", "Shopee", "Siêu sale 11.11", "₫99.000"),
    ]
    r = gmail_sync.sync(conn)
    assert (r["imported"], r["duplicate"], r["cancelled"], r["skipped"]) == (2, 1, 1, 1)
    rows = conn.execute("SELECT order_id, status FROM transactions ORDER BY order_id").fetchall()
    assert [tuple(x) for x in rows] == [("261001AAAA1111", "ok"), ("261002BBBB2222", "cancelled")]


def test_same_day_shipping_email_before_purchase_still_gets_product_name(conn, mailbox):
    gmail_sync.add_account(conn, "lan@gmail.com", "abcdefghijklmnop")
    mailbox["lan@gmail.com"] = [  # IMAP returns them in any order; the timestamp decides
        shopee("261005CCCC3333", 300_000, "2026-10-05T18:00:00", "Đơn hàng #261005CCCC3333 đang được giao"),
        shopee("261005CCCC3333", 300_000, "2026-10-05T08:00:00"),
    ]
    gmail_sync.sync(conn)
    [row] = conn.execute("SELECT description FROM transactions").fetchall()
    assert row[0] == "Kem chống nắng Anessa"


def test_resync_is_idempotent(conn, mailbox):
    gmail_sync.add_account(conn, "lan@gmail.com", "abcdefghijklmnop")
    mailbox["lan@gmail.com"] = [shopee("261006DDDD4444", 100_000, "2026-10-06T08:00:00")]
    gmail_sync.sync(conn)
    gmail_sync.sync(conn)  # the fake returns the same email again; the real one skips known Message-IDs
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_one_failing_account_does_not_block_others(conn, mailbox):
    gmail_sync.add_account(conn, "lan@gmail.com", "abcdefghijklmnop")
    gmail_sync.add_account(conn, "hao@gmail.com", "abcdefghijklmnop")
    mailbox["lan@gmail.com"] = OSError("network down")
    mailbox["hao@gmail.com"] = [shopee("261007EEEE5555", 100_000, "2026-10-07T08:00:00")]
    r = gmail_sync.sync(conn)
    assert r["imported"] == 1
    assert r["errors"] == ["Không kết nối được Gmail (lan@gmail.com) — kiểm tra mạng Wi-Fi rồi thử lại."]


def test_sync_without_accounts_explains(conn, fake_keyring):
    with pytest.raises(gmail_sync.SyncError, match="Chưa kết nối"):
        gmail_sync.sync(conn)


def test_reparse_after_parser_fix(conn, mailbox, monkeypatch):
    gmail_sync.add_account(conn, "lan@gmail.com", "abcdefghijklmnop")
    odd = ("2026-10-08T08:00:00", "<odd>", "Shopee", "Xác nhận đơn hàng #261008FFFF6666",
           "Mã đơn hàng 261008FFFF6666\nSố tiền phải trả\n150.000đ")
    mailbox["lan@gmail.com"] = [odd]
    monkeypatch.setattr(parsers, "TOTAL_LABELS", ["khong co nhan nay"])
    monkeypatch.setattr(parsers, "find_money", lambda t: [])  # simulate an unparseable template
    assert gmail_sync.sync(conn)["no_amount"] == 1
    monkeypatch.undo()
    assert gmail_sync.reparse(conn)["imported"] == 1


MOMO_PAY = """Ví MoMo
Giao dịch thành công
Dịch vụ: Tiền điện EVN HCMC
Nhà cung cấp: Tổng công ty Điện lực TP.HCM
Số tiền: 1.250.000đ
Thời gian: 10:15 - 12/10/2026
Mã giao dịch: 41234567890"""

MOMO_IN = """Ví MoMo
Bạn đã nhận tiền thành công
Người chuyển: NGUYEN VAN A
Số tiền: 500.000đ
Lời nhắn: tra tien an trua
Mã giao dịch: 41234567891"""


def test_momo_payment_and_incoming_money(conn, mailbox):
    gmail_sync.add_account(conn, "lan@gmail.com", "abcdefghijklmnop")
    mailbox["lan@gmail.com"] = [
        ("2026-10-12T10:16:00", "<m1>", "MoMo <no-reply@momo.vn>", "Giao dịch thành công", MOMO_PAY),
        ("2026-10-12T11:00:00", "<m2>", "MoMo <no-reply@momo.vn>", "Bạn đã nhận tiền thành công", MOMO_IN),
        ("2026-10-13T09:00:00", "<m3>", "MoMo <no-reply@momo.vn>", "Ưu đãi thanh toán hoá đơn giảm 50.000đ", "50.000đ"),
    ]
    r = gmail_sync.sync(conn)
    assert (r["imported"], r["skipped"]) == (2, 1)
    rows = conn.execute("SELECT t.source, t.kind, t.amount, t.description, t.order_id, c.name FROM transactions t "
                        "JOIN categories c ON c.id = t.category_id ORDER BY t.amount DESC").fetchall()
    assert [tuple(x) for x in rows] == [
        ("momo", "expense", 1_250_000, "Tiền điện EVN HCMC", "41234567890", "Điện nước"),
        ("momo", "income", 500_000, "tra tien an trua", "41234567891", "Thu nhập khác"),
    ]


def test_survey_and_career_emails_are_skipped(conn, mailbox):
    gmail_sync.add_account(conn, "lan@gmail.com", "abcdefghijklmnop")
    mailbox["lan@gmail.com"] = [
        ("2026-06-25T09:00:00", "<s>", "Shopee <info@mail.shopee.vn>", "Xin chào lan, Shopee muốn lắng nghe ý kiến của bạn!", "Khảo sát"),
        ("2026-06-30T09:00:00", "<c>", "Shopee Careers <no-reply.hr@shopee.com>", "Thank you for your application at Shopee", ""),
    ]
    assert gmail_sync.sync(conn)["skipped"] == 2
