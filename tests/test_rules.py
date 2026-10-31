import pytest

import rules


def name(conn, cid):
    return conn.execute("SELECT name FROM categories WHERE id = ?", (cid,)).fetchone()[0]


@pytest.mark.parametrize("text,want", [
    ("Học phí tháng 11 bé An", "Học phí"), ("HỌC PHÍ", "Học phí"), ("hoc phi", "Học phí"),
    ("Tiền điện EVN tháng 10", "Điện nước"), ("Áo thun nam cotton", "Quần áo & giày dép"),
    ("Son kem lì Romand", "Mỹ phẩm & làm đẹp"), ("Serum Vitamin C Klairs", "Mỹ phẩm & làm đẹp"),
    ("Vitamin tổng hợp", "Sức khoẻ & thuốc"), ("Đi ăn nhà hàng cuối tuần", "Ăn uống & đi chợ"),
    ("Thứ gì đó lạ hoắc", "Khác"),
])
def test_categorize(conn, text, want):
    assert name(conn, rules.categorize(conn, text)) == want


def test_whole_words_only(conn):
    # "ao" (áo) must not match inside "bao" or "giao"
    assert name(conn, rules.categorize(conn, "Phí giao hàng bao bì")) == "Khác"


def test_income_uses_income_categories(conn):
    assert name(conn, rules.categorize(conn, "Lương tháng 10", "income")) == "Lương"
    assert name(conn, rules.categorize(conn, "Bán đồ cũ", "income")) == "Thu nhập khác"


def test_normalize():
    assert rules.normalize("  Đồ   GIA dụng ") == "do gia dung"
