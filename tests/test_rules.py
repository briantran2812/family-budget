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



def test_keyword_additions_reach_existing_databases_once(fresh_db):
    import db
    import rules
    with db.connect() as c:
        c.execute("DELETE FROM rules WHERE keyword IN ('pho bo', 'tnhh')")    # a database from before 1.4.0
        c.execute("DELETE FROM settings WHERE key = 'keywords_version'")
        cid = lambda n: c.execute("SELECT id FROM categories WHERE name = ?", (n,)).fetchone()[0]
        c.execute("UPDATE rules SET category_id = ? WHERE keyword = 'tra da'", (cid("Khác"),))  # the user's own choice
    db.init()
    with db.connect() as c:
        cat = lambda text, kind="expense": c.execute("SELECT name FROM categories WHERE id = ?",
                                                     (rules.categorize(c, text, kind),)).fetchone()[0]
        assert cat("Phở bò Hà Nội") == "Ăn uống & đi chợ"
        assert cat("Tiền chuyển vào (B/O CONG TY TNHH ABC...", "income") == "Lương"
        assert cat("Trà đá vỉa hè") == "Khác"                              # INSERT OR IGNORE keeps the user's mapping
        assert cat("Thanh toán cho VO NGOC QUYET") == "Khác"                # bare "cho" is not chợ
        assert cat("Chuyen tien cho me") == "Khác"                          # nor is "tiền cho"
        assert cat("Đi phố đi bộ") == "Khác"                                # bare "pho" is not phở
        c.execute("DELETE FROM rules WHERE keyword = 'pho bo'")             # the user removes a new keyword…
    db.init()
    with db.connect() as c:
        assert not c.execute("SELECT 1 FROM rules WHERE keyword = 'pho bo'").fetchone()   # …and it stays removed


def test_fresh_database_has_the_additions():
    import db
    from rules import normalize
    names = {normalize(k) for adds in db.KEYWORD_ADDITIONS.values() for kws in adds.values() for k in kws}
    defaults = {normalize(k) for _, _, _, kws in db.DEFAULT_CATEGORIES for k in kws}
    assert not names & {"pho", "cho", "com", "chao", "lau"}
    assert not names & defaults, "a keyword listed in both places"
