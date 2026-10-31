import pytest

import parsers
from samples import shopee_email, tiktok_email


@pytest.mark.parametrize("text,want", [
    ("123.000đ", 123000), ("₫1.234.567", 1234567), ("1,500,000 VND", 1500000), ("Giá 45.000 ₫", 45000),
    ("-₫50.000", 50000), ("VNĐ 2.000.000", 2000000), ("120.000 đồng", 120000),
])
def test_money_formats(text, want):
    assert parsers.find_money(text)[0][0] == want


@pytest.mark.parametrize("text", ["x2 sản phẩm", "giảm 50%", "size 39", "500đ"])
def test_not_money(text):
    assert parsers.find_money(text) == []


@pytest.mark.parametrize("text,want", [
    ("Thời gian 14:32 - 10/10/2026", "2026-10-10"), ("Ngày đặt 2026-09-01", "2026-09-01"),
    ("31/02/2026 rồi 01/03/2026", "2026-03-01"),  # invalid date skipped
])
def test_dates(text, want):
    assert parsers.find_date(text) == want


def test_html_to_text_drops_style_and_script():
    text = parsers.html_to_text("<style>.a{}</style><script>x()</script><p>Xin&nbsp;chào</p><td>₫1.000</td>")
    assert "x()" not in text and ".a" not in text
    assert text.splitlines() == ["Xin chào", "₫1.000"]


def test_shopee_order_total_includes_shipping_and_voucher():
    items = [("Kem chống nắng Anessa 60ml", 1, 465_000), ("Sữa rửa mặt CeraVe 236ml", 2, 320_000)]
    body = parsers.html_to_text(shopee_email("241031ABCD1234", items, 15_000, 50_000))
    r = parsers.parse_order_email("Xác nhận đơn hàng #241031ABCD1234", body, "Shopee <info@mail.shopee.vn>", "<m>")
    assert r == {"status": "purchase", "platform": "shopee", "order_id": "241031ABCD1234",
                 "amount": 465_000 + 640_000 + 15_000 - 50_000,
                 "description": "Kem chống nắng Anessa 60ml · Sữa rửa mặt CeraVe 236ml"}


def test_tiktok_order():
    body = tiktok_email("577612345678901234", [("Bỉm quần Bobby size L", 1, 345_000)])
    r = parsers.parse_order_email("Đơn hàng của bạn đã được đặt", body, "TikTok Shop <noreply@shop.tiktok.com>", "<m>")
    assert (r["platform"], r["order_id"], r["amount"]) == ("tiktok", "577612345678901234", 345_000)
    assert r["description"] == "Bỉm quần Bobby size L"


def test_product_name_with_label_word_is_kept():
    # "tổng hợp" once matched the "tong" label filter and the product name was lost
    body = tiktok_email("577612345678901235", [("Vitamin tổng hợp Centrum 100 viên", 1, 520_000)])
    r = parsers.parse_order_email("Đơn hàng mới", body, "tiktok", "<m>")
    assert r["description"] == "Vitamin tổng hợp Centrum 100 viên"


def test_cancel_email():
    r = parsers.parse_order_email("Đơn hàng #241031ABCD1234 đã bị hủy", "Mã đơn hàng: 241031ABCD1234",
                                  "Shopee", "<m>")
    assert (r["status"], r["order_id"]) == ("cancelled", "241031ABCD1234")


def test_shipping_email_without_price():
    r = parsers.parse_order_email("Đơn hàng #241031ABCD1234 đã giao thành công",
                                  "Đơn hàng #241031ABCD1234 đã được giao. Đánh giá ngay!", "Shopee", "<m>")
    assert r["status"] == "no_amount"


def test_order_id_needs_a_digit():
    r = parsers.parse_order_email("Đơn hàng thanhcong", "Đơn hàng thanhcong\nTổng cộng 100.000đ", "Shopee", "<abc>")
    assert r["order_id"].startswith("MSG-")  # falls back to a per-email id instead of "THANHCONG"


def test_ocr_rows_order_list():
    rows = ["Đơn mua", "Cocoon Official Store", "Nước tẩy trang bí đao Cocoon 500ml", "₫195.000",
            "Thành tiền: ₫180.000", "Nhà Cửa Đời Sống", "Nước giặt Omo Matic 3.6kg", "Thành tiền: ₫215.000",
            "Ngày đặt 28/10/2026"]
    got = [(c["amount"], c["description"], c["date"], c["selected"]) for c in parsers.parse_ocr_rows(rows)]
    assert got == [(180000, "Nước tẩy trang bí đao Cocoon 500ml", "2026-10-28", True),
                   (215000, "Nước giặt Omo Matic 3.6kg", "2026-10-28", True)]


def test_ocr_rows_receipt_label_without_colon():
    rows = ["✓ Giao dịch thành công", "-1.250.000đ", "Dịch vụ Tiền điện EVN HCMC kỳ tháng 10",
            "Số tiền 1.250.000đ", "Thời gian 14:32 - 10/10/2026"]
    [c] = parsers.parse_ocr_rows(rows)
    assert (c["amount"], c["description"], c["date"]) == (1_250_000, "Tiền điện EVN HCMC kỳ tháng 10", "2026-10-10")


def test_ocr_rows_unlabelled_preselects_largest():
    cands = parsers.parse_ocr_rows(["Cà phê sữa", "35.000đ", "Bánh mì", "25.000đ"])
    assert [c["selected"] for c in cands] == [True, False]


def test_email_datetime_keeps_time():
    assert parsers.email_datetime("Fri, 31 Oct 2026 09:15:00 +0700")[11:16] in {"09:15", "10:15"}
