"""SQLite storage. One file per user: ~/Library/Application Support/ThuChiGiaDinh/budget.db."""
import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.environ.get("BUDGET_DATA") or Path.home() / "Library" / "Application Support" / "ThuChiGiaDinh")
DB_PATH = Path(os.environ.get("BUDGET_DB") or DATA_DIR / "budget.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL,
    kind  TEXT NOT NULL DEFAULT 'expense',      -- expense | income
    sort  INTEGER NOT NULL DEFAULT 0,
    icon  TEXT NOT NULL DEFAULT '📦',
    budget INTEGER                               -- monthly limit in VND, NULL = none
);
CREATE TABLE IF NOT EXISTS rules (
    id          INTEGER PRIMARY KEY,
    keyword     TEXT UNIQUE NOT NULL,            -- stored unaccented, lowercase
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY,
    date        TEXT NOT NULL,                   -- YYYY-MM-DD
    amount      INTEGER NOT NULL,                -- VND, always positive
    kind        TEXT NOT NULL DEFAULT 'expense', -- expense | income
    description TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT 'manual',  -- manual | shopee | tiktok | screenshot
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    order_id    TEXT,
    status      TEXT NOT NULL DEFAULT 'ok',      -- ok | cancelled
    pay_account TEXT,                            -- how it was paid, e.g. "Visa Techcombank"; NULL = unknown
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source, order_id)
);
CREATE INDEX IF NOT EXISTS ix_tx_date ON transactions(date);
CREATE TABLE IF NOT EXISTS emails (
    message_id     TEXT PRIMARY KEY,
    received       TEXT,
    sender         TEXT,
    subject        TEXT,
    body           TEXT,                         -- kept so "Phân tích lại" works without re-downloading
    status         TEXT,                         -- imported | duplicate | cancelled | no_amount | skipped
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS statements (
    id          INTEGER PRIMARY KEY,
    account     TEXT NOT NULL,                   -- card/account label, matched against transactions.pay_account
    filename    TEXT,
    file_sha    TEXT UNIQUE,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS statement_lines (
    id           INTEGER PRIMARY KEY,
    statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    date         TEXT NOT NULL,
    amount       INTEGER NOT NULL,
    kind         TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    status       TEXT,                           -- NULL | auto | manual | added | ignored
    match_tx_id  INTEGER REFERENCES transactions(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    kind        TEXT NOT NULL,                   -- budget | phone | gmail | version | error | piggy
    icon        TEXT NOT NULL DEFAULT '🔔',
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    link        TEXT,                            -- JSON: {tab, cat, src, whatsnew, piggy}
    dedupe      TEXT UNIQUE,
    read_at     TEXT
);
CREATE TABLE IF NOT EXISTS piggy (                -- 🐷 Ống heo: one snapshot per closed month
    month       TEXT PRIMARY KEY,                -- YYYY-MM
    income      INTEGER NOT NULL,
    expense     INTEGER NOT NULL,
    saved       INTEGER NOT NULL,                -- income − expense, may be negative
    recorded_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    note        TEXT
);
CREATE TABLE IF NOT EXISTS usage_events (         -- Thống kê sử dụng (usage.py), kept 60 days
    id     INTEGER PRIMARY KEY,
    at     TEXT NOT NULL,                        -- local time, YYYY-MM-DD HH:MM:SS
    kind   TEXT NOT NULL,                        -- open | screenshot | phone_sync | tx_add | error | …
    detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_usage_kind_at ON usage_events(kind, at);
"""

DEFAULT_CATEGORIES = [
    # (name, kind, icon, keywords) — keywords are matched without accents, on whole words.
    ("Học phí", "expense", "🎓", ["hoc phi", "tuition", "mam non", "truong hoc", "khoa hoc", "lop hoc", "trung tam anh ngu"]),
    ("Điện nước", "expense", "💡", ["tien dien", "evn", "dien luc", "tien nuoc", "cap nuoc", "nuoc sach", "sawaco"]),
    ("Internet & điện thoại", "expense", "📶", ["internet", "cuoc dien thoai", "nap tien dien thoai", "viettel", "vnpt",
                                          "fpt telecom", "mobifone", "vinaphone", "sim"]),
    ("Mỹ phẩm & làm đẹp", "expense", "💄", ["my pham", "son moi", "son kem", "son duong", "son tint", "kem chong nang",
                                      "sua rua mat", "serum", "toner", "mat na", "duong da", "duong am", "tay trang",
                                      "nuoc hoa", "kem nen", "phan ma", "mascara", "dau goi", "dau xa", "sua tam",
                                      "lipstick", "sunscreen", "skincare", "cerave", "la roche", "innisfree",
                                      "loreal", "bioderma", "cocoon", "sap tay trang", "vitamin c", "serum vitamin"]),
    ("Ăn uống & đi chợ", "expense", "🛒", ["thuc pham", "do an", "gao", "sua tuoi", "banh", "keo", "ca phe", "tra sua",
                                     "mi tom", "gia vi", "nuoc mam", "dau an", "hat dieu", "trai cay", "grabfood",
                                     "shopeefood", "bach hoa xanh", "winmart", "coopmart", "an vat", "nha hang", "quan an", "an uong", "di cho", "pizza", "coffee", "highlands", "coffee house", "lotte mart", "circle k", "bun cha", "grab food", "baemin"]),
    ("Đồ gia dụng", "expense", "🏠", ["noi", "chao", "chen", "bat dia", "khan", "nuoc giat", "nuoc xa vai",
                                "nuoc rua chen", "giay ve sinh", "khan giay", "ga giuong", "chan goi", "hop dung",
                                "binh nuoc", "may hut", "quat", "den", "gia dung", "tui rac", "moc ao"]),
    ("Quần áo & giày dép", "expense", "👗", ["ao", "quan", "vay", "dam", "giay", "dep", "tui xach", "balo", "tat",
                                       "ao khoac", "ao thun", "so mi", "do lot", "thoi trang", "uniqlo", "zara", "h&m"]),
    ("Mẹ & bé", "expense", "🍼", ["bim", "ta dan", "ta quan", "sua cong thuc", "binh sua", "do choi", "xe day", "em be",
                            "tre em", "so sinh", "huggies", "bobby", "merries", "moony", "cho be"]),
    ("Sức khoẻ & thuốc", "expense", "💊", ["thuoc", "vitamin", "khau trang", "nha thuoc", "benh vien", "kham benh",
                                     "long chau", "pharmacity", "thuc pham chuc nang", "nhiet ke", "bao hiem y te"]),
    ("Đi lại & xăng xe", "expense", "🚗", ["xang", "grab", "grabbike", "grabcar", "xanh sm", "gojek", "ve may bay",
                                     "vietjet", "vietnam airlines", "gui xe", "vetc", "phi duong bo"]),
    ("Giải trí & du lịch", "expense", "🎬", ["netflix", "spotify", "youtube premium", "cgv", "ve xem phim", "khach san",
                                       "du lich", "agoda", "traveloka", "booking"]),
    ("Điện tử & phụ kiện", "expense", "📱", ["tai nghe", "cap sac", "cu sac", "op lung", "dien thoai", "laptop", "chuot",
                                       "ban phim", "loa", "pin du phong", "the nho", "usb"]),
    ("Khác", "expense", "📦", []),
    ("Lương", "income", "💼", ["luong", "salary"]),
    ("Thu nhập khác", "income", "💰", []),
]


# Default keywords added after a release. A fresh database gets them with DEFAULT_CATEGORIES; an existing one gets each
# version's list once (tracked by setting "keywords_version"), so a keyword the user later deletes stays deleted.
# Bare "pho", "cho", "com", "chao", "lau" and "tien cho" are avoided: unaccented they also mean phố, "cho" (for),
# ".com", chảo, lau nhà and "chuyển tiền cho mẹ".
KEYWORD_ADDITIONS = {
    "1.4.0": {
        "Lương": ["cong ty", "tnhh", "co phan", "payroll", "luong thang", "tien thuong"],
        "Ăn uống & đi chợ": ["pho bo", "pho ga", "bun bo", "bun rieu", "bun thit nuong", "banh mi", "banh cuon",
                             "hu tieu", "com tam", "com ga", "com trua", "an sang", "an trua", "an toi", "an lau", "lau thai",
                             "tra da", "nuoc mia", "sinh to", "gofood", "be food", "lotteria", "kfc", "jollibee",
                             "mcdonald", "phuc long", "katinat", "starbucks", "trung nguyen", "cong ca phe"],
        "Đi lại & xăng xe": ["taxi", "mai linh", "vinasun", "do xang", "petrolimex", "rua xe", "sua xe", "thay nhot"],
    },
}


def _add_keywords(conn: sqlite3.Connection, additions: dict[str, list[str]]) -> None:
    from rules import normalize
    for name, keywords in additions.items():
        row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
        if row:  # the user may have renamed or deleted the category; then there is nothing to add to
            conn.executemany("INSERT OR IGNORE INTO rules(keyword, category_id) VALUES (?, ?)",
                             [(normalize(k), row[0]) for k in keywords])


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init() -> None:
    from rules import normalize

    with connect() as conn:
        conn.executescript(SCHEMA)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(categories)")}
        if "icon" not in cols:  # databases created by the first version
            conn.execute("ALTER TABLE categories ADD COLUMN icon TEXT NOT NULL DEFAULT '📦'")
            conn.execute("ALTER TABLE categories ADD COLUMN budget INTEGER")
            for name, _kind, icon, _kw in DEFAULT_CATEGORIES:
                conn.execute("UPDATE categories SET icon = ? WHERE name = ?", (icon, name))
        if "pay_account" not in {r[1] for r in conn.execute("PRAGMA table_info(transactions)")}:
            conn.execute("ALTER TABLE transactions ADD COLUMN pay_account TEXT")  # added in 1.3.0
        if not conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]:
            for sort, (name, kind, icon, keywords) in enumerate(DEFAULT_CATEGORIES):
                cid = conn.execute("INSERT INTO categories(name, kind, sort, icon) VALUES (?, ?, ?, ?)",
                                   (name, kind, sort, icon)).lastrowid
                for kw in keywords:
                    conn.execute("INSERT OR IGNORE INTO rules(keyword, category_id) VALUES (?, ?)",
                                 (normalize(kw), cid))
        done = get_setting(conn, "keywords_version")
        as_tuple = lambda v: tuple(int(x) for x in v.split("."))
        for version in sorted(KEYWORD_ADDITIONS, key=as_tuple):
            if not done or as_tuple(version) > as_tuple(done):
                _add_keywords(conn, KEYWORD_ADDITIONS[version])
        if KEYWORD_ADDITIONS:
            set_setting(conn, "keywords_version", max(KEYWORD_ADDITIONS, key=as_tuple))


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO settings(key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
