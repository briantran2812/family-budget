"""Keyword → category rules. Matching ignores accents and case, on whole words; the longest keyword wins."""
import re
import sqlite3
import unicodedata


def normalize(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def load(conn: sqlite3.Connection) -> list[tuple[re.Pattern, str, int]]:
    rows = conn.execute("SELECT keyword, category_id FROM rules").fetchall()
    compiled = [(re.compile(r"(?<!\w)" + re.escape(r["keyword"]) + r"(?!\w)"), r["keyword"], r["category_id"])
                for r in rows]
    return sorted(compiled, key=lambda x: -len(x[1]))


def categorize(conn: sqlite3.Connection, text: str, kind: str = "expense",
               compiled: list | None = None) -> int | None:
    """Return the category id for `text`, or the kind's fallback category ("Khác" / "Thu nhập khác")."""
    norm = normalize(text)
    kinds = dict(conn.execute("SELECT id, kind FROM categories").fetchall())
    for pattern, _kw, cid in compiled if compiled is not None else load(conn):
        if kinds.get(cid) == kind and pattern.search(norm):
            return cid
    fallback = "Khác" if kind == "expense" else "Thu nhập khác"
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (fallback,)).fetchone()
    if row:
        return row["id"]
    row = conn.execute("SELECT id FROM categories WHERE kind = ? ORDER BY sort DESC LIMIT 1", (kind,)).fetchone()
    return row["id"] if row else None
