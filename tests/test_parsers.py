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


# ---------------------------------------------------------------- history screens (MoMo "Giao dịch gần đây")

MOMO_HISTORY = [  # OCR rows as macOS Vision returns them for the real screen; names changed
    "3:01 #", "Q Tìm kiếm giao dịch", "Giao dịch gần đây", "Tháng 11/2026",
    "Tiền lời Túi Thần Tài ngày +270đ", "01/11/2026 Số dư Túi: 2.471.829đ", "02:55 - 02/11",
    "Tổng tiền lời tháng 11 558đ >",
    "Thanh toán cho NGUYEN VAN -80.000đ", "AN (Techcombank) Số dư Túi: 21.515đ", "14:11 - 01/11",
    "Thanh toán HIGHLANDS -86.000d", "COFFEE Số dư Túi: 2.551.559đ", "13:10 - 01/11",
    "Tháng 10/2026",
    "Thanh toán cho PAYOO -165.000đ", "Aeon Mall Tan Phu Celado... Số dư Túi: 2.637.271đ", "17:47 - 31/10",
    "Tiền lời Túi Thần Tài ngày +306đ", "30/10/2026 Số dư Túi: 2.802.2710", "02:45 - 31/10",
    "Tổng tiền lời tháng 10 12.590đ >",
    "Thanh toán cho CONG TY -98.000đ",  # cut off by the tab bar: no time line
    "MoMo Ưu đãi Giao dịch Tôi",
]


def test_momo_history_screen():
    got = parsers.parse_ocr_rows(MOMO_HISTORY)
    assert [(c["date"], c["amount"], c["description"], c["pay_account"]) for c in got] == [
        ("2026-11-01", 80_000, "NGUYEN VAN AN (Techcombank)", "Ví MoMo"),
        ("2026-11-01", 86_000, "HIGHLANDS COFFEE", "Ví MoMo"),
        ("2026-10-31", 165_000, "PAYOO Aeon Mall Tan Phu Celado...", "Ví MoMo"),
    ]
    assert all(c["selected"] for c in got)


def test_history_without_month_header_rolls_back_a_year():
    from datetime import date
    rows = ["Thanh toán Grab -45.000đ", "08:10 - 30/12", "Thanh toán Circle K -25.000đ", "21:40 - 28/12"]
    got = parsers.parse_history(rows, today=date(2027, 1, 3))
    assert [c["date"] for c in got] == ["2026-12-30", "2026-12-28"]
    assert parsers.detect_source(rows) is None  # nothing says which wallet or bank


def test_bank_app_history_style():
    rows = ["Hôm nay", "Chuyển tiền cho TRAN THI B - 250,000 VND", "09:15 - 02/11/2026",
            "Nhận tiền từ CONG TY X + 15,000,000 VND", "08:00 - 01/11/2026"]
    got = parsers.parse_history(rows)
    assert [(c["date"], c["amount"], c["description"]) for c in got] == [
        ("2026-11-02", 250_000, "Chuyển tiền cho TRAN THI B")]


def test_single_receipt_is_not_a_history_screen():
    assert parsers.parse_history(["Thanh toán thành công", "-6.500.000đ", "14:32 - 10/10/2026"]) is None



@pytest.mark.parametrize("rows, want", [
    (MOMO_HISTORY, "Ví MoMo"),  # its payee "(Techcombank)" is the receiver's bank, not the source
    (["Ví MoMo", "Giao dịch thành công", "-1.107.000đ", "Nguồn tiền Ví MoMo"], "Ví MoMo"),
    (["Techcombank", "Chuyển khoản thành công", "250.000 VND", "Người nhận TRAN B"], "Techcombank"),
    (["Chuyển tiền thành công", "Tài khoản nguồn: 1903****123 - Vietcombank", "Người nhận NGUYEN C (ACB)"], "Vietcombank"),
    (["Giao dịch thành công", "Thanh toán bằng: ZaloPay", "-45.000đ"], "Ví ZaloPay"),
    (["Đơn mua", "Kem chống nắng", "Thành tiền: ₫465.000"], None),
    (["Chuyển tiền cho LE D (Techcombank) -50.000đ", "10:00 - 01/11", "Thanh toán X -20.000đ", "11:00 - 01/11"], None),
])
def test_detect_source(rows, want):
    assert parsers.detect_source(rows) == want
