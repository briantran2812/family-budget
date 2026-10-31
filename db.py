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
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
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
                                     "shopeefood", "bach hoa xanh", "winmart", "coopmart", "an vat", "nha hang", "quan an", "an uong", "di cho"]),
    ("Đồ gia dụng", "expense", "🏠", ["noi", "chao", "chen", "bat dia", "khan", "nuoc giat", "nuoc xa vai",
                                "nuoc rua chen", "giay ve sinh", "khan giay", "ga giuong", "chan goi", "hop dung",
                                "binh nuoc", "may hut", "quat", "den", "gia dung", "tui rac", "moc ao"]),
    ("Quần áo & giày dép", "expense", "👗", ["ao", "quan", "vay", "dam", "giay", "dep", "tui xach", "balo", "tat",
                                       "ao khoac", "ao thun", "so mi", "do lot", "thoi trang"]),
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
        if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]:
            return
        for sort, (name, kind, icon, keywords) in enumerate(DEFAULT_CATEGORIES):
            cid = conn.execute("INSERT INTO categories(name, kind, sort, icon) VALUES (?, ?, ?, ?)",
                               (name, kind, sort, icon)).lastrowid
            for kw in keywords:
                conn.execute("INSERT OR IGNORE INTO rules(keyword, category_id) VALUES (?, ?)",
                             (normalize(kw), cid))


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO settings(key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
