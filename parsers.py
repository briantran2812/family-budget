"""Turn email text and OCR text into transactions — no network, no AI, just patterns.

Shopee/TikTok change their email templates without notice. When an email stops parsing, it lands in
the "Email chưa đọc được" list in the app; adjust the keyword lists below and press "Phân tích lại".
"""
import hashlib
import re
from datetime import date, datetime
from html.parser import HTMLParser

from rules import normalize

# ---------------------------------------------------------------- money & dates

_NUM = r"(\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]00)?"
MONEY_RE = re.compile(
    rf"(?:₫|VNĐ|VND)\s*{_NUM}"            # ₫123.000, VND 123,000
    rf"|{_NUM}\s*(?:₫|đ|đồng|VNĐ|VND)(?!\w)",  # 123.000đ, 123.000 ₫, 123,000 VND
    re.IGNORECASE,
)


def find_money(text: str) -> list[tuple[int, int]]:
    """Every amount in `text` as (value_vnd, position)."""
    out = []
    for m in MONEY_RE.finditer(text):
        raw = m.group(1) or m.group(2)
        value = int(re.sub(r"[.,]", "", raw))
        if value >= 1000:  # below 1.000đ is a quantity or a percentage, not a price
            out.append((value, m.start()))
    return out


DATE_RES = [
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b"), ("d", "m", "y")),
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), ("y", "m", "d")),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2})\b"), ("d", "m", "y")),  # 02/11/26
]
DATE_LABELS = ("thoi gian", "ngay giao dich", "ngay thanh toan", "ngay gd", "ngay", "time", "date")


def find_date(text: str, today: date | None = None) -> str | None:
    """First real date in `text` that is not in the future (an expiry or due date is not when you paid)."""
    latest = today or date.today()
    for regex, order in DATE_RES:
        for m in regex.finditer(text):
            parts = dict(zip(order, map(int, m.groups())))
            y = parts["y"] + 2000 if parts["y"] < 100 else parts["y"]
            try:
                d = date(y, parts["m"], parts["d"])
            except ValueError:
                continue
            if d <= latest:
                return d.isoformat()
    return None


def receipt_date(rows: list[str], today: date | None = None) -> str | None:
    """The date next to a "Thời gian / Ngày giao dịch" label wins over any other date on the screen."""
    for i, row in enumerate(rows):
        if normalize(row).startswith(DATE_LABELS):
            if found := find_date(" ".join(rows[i:i + 2]), today):
                return found
    return find_date("\n".join(rows), today)


# ---------------------------------------------------------------- HTML → text

class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "tr", "br", "li", "h1", "h2", "h3", "h4", "table", "td", "th"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    lines = (re.sub(r"[ \t ]+", " ", ln).strip() for ln in "".join(p.parts).splitlines())
    return "\n".join(ln for ln in lines if ln)


# ---------------------------------------------------------------- order emails

# Matched against unaccented lowercase text. Order matters: the first label found wins.
TOTAL_LABELS = ["tong thanh toan", "tong so tien thanh toan", "tong so tien", "so tien thanh toan",
                "thanh tien", "tong cong", "tong tien", "total payment", "order total", "grand total",
                "amount paid", "total"]
ORDER_ID_RE = re.compile(r"(?:ma don hang|ma don|ma giao dich|order id|order no\.?|order number|order sn|"
                         r"transaction id|don hang)"
                         r"\s*[#:.]?\s*#?\s*(?=[a-z]*\d)([a-z0-9]{8,24})\b")  # an id has a digit; "thanhcong" is not one
CANCEL_WORDS = ["da huy", "huy don", "da bi huy", "cancelled", "canceled", "hoan tien", "refund",
                "tra hang"]
PROMO_WORDS = ["uu dai", "khuyen mai", "giam gia", "voucher", "qua tang", "sale", "flash", "hoan xu",
               "tich diem", "su kien", "moi ban", "nhan ngay"]
INCOME_WORDS = ["nhan tien", "nhan duoc", "da nhan", "tien vao", "chuyen den ban", "received"]
NOT_ITEM = re.compile(r"(?<!\w)(?:phi van chuyen|giam gia|voucher|tam tinh|so luong|tong cong|tong tien|"
                      r"tong thanh toan|thanh tien|ma don|order|dia chi|nguoi nhan|thanh toan|phuong thuc|"
                      r"shopee|tiktok|ngay dat|van chuyen|hotline|lien he|copyright|email|xin chao|cam on|"
                      r"don hang|trang thai|giao hang|phi dich vu|thue vat)(?!\w)")  # whole words only


def platform_of(sender: str) -> str:
    s = (sender or "").lower()
    if "shopee" in s:
        return "shopee"
    if "tiktok" in s:
        return "tiktok"
    if "momo" in s:
        return "momo"
    return "other"


def _guess_items(lines: list[str]) -> str:
    """Product names are the long, price-free lines that are not labels."""
    names = []
    for ln in lines:
        norm = normalize(ln)
        if len(ln) < 8 or len(ln) > 160 or find_money(ln) or not re.search(r"[a-z]{3}", norm):
            continue
        if NOT_ITEM.search(norm) or "@" in ln or "http" in norm:
            continue
        names.append(ln)
        if len(names) == 3:
            break
    return " · ".join(names)


def parse_payment_email(subject: str, body: str, platform: str, message_id: str) -> dict:
    """E-wallet receipts (MoMo): one amount, a service/recipient line, maybe incoming money."""
    lines = [ln for ln in body.splitlines() if ln.strip()]
    norm_subject = normalize(subject)
    kind = "income" if any(w in norm_subject or w in normalize(body[:400]) for w in INCOME_WORDS) else "expense"
    m = ORDER_ID_RE.search(normalize(f"{subject}\n{body}"))
    order_id = m.group(1).upper() if m else "MSG-" + hashlib.sha1(message_id.encode()).hexdigest()[:12]
    cands = parse_ocr_rows(lines)  # same label rules as a receipt screenshot
    pick = next((c for c in cands if c["selected"]), None)
    if not pick:
        return {"status": "no_amount", "platform": platform, "order_id": order_id, "amount": None,
                "description": subject, "kind": kind}
    return {"status": "purchase", "platform": platform, "order_id": order_id, "amount": pick["amount"],
            "description": pick["description"] or subject, "kind": kind}


def parse_order_email(subject: str, body: str, sender: str, message_id: str) -> dict:
    """Return {'status', 'platform', 'order_id', 'amount', 'description'}.

    status is one of: purchase, cancelled, no_amount.
    """
    text = f"{subject}\n{body}"
    norm = normalize(text)
    platform = platform_of(sender)

    m = ORDER_ID_RE.search(norm)
    order_id = m.group(1).upper() if m else None

    if any(w in normalize(subject) for w in CANCEL_WORDS):
        return {"status": "cancelled", "platform": platform, "order_id": order_id,
                "amount": None, "description": subject}

    # Find the total: first label in TOTAL_LABELS order, then the first amount on or after its line.
    amount = None
    lines = [ln for ln in body.splitlines() if ln.strip()]
    norm_lines = [normalize(ln) for ln in lines]
    for label in TOTAL_LABELS:
        for i, nl in enumerate(norm_lines):
            if label in nl:
                window = " ".join(lines[i:i + 3])  # the amount can sit in the next table cell
                money = find_money(window)
                if money:
                    amount = money[0][0]
                    break
        if amount:
            break
    if amount is None:
        money = find_money(body)
        if money:
            amount = max(v for v, _ in money)  # the total is the largest number in an order email
    if amount is None:
        return {"status": "no_amount", "platform": platform, "order_id": order_id,
                "amount": None, "description": subject}

    if not order_id:
        order_id = "MSG-" + hashlib.sha1(message_id.encode()).hexdigest()[:12]

    description = _guess_items(lines) or subject
    return {"status": "purchase", "platform": platform, "order_id": order_id,
            "amount": amount, "description": description}


# ---------------------------------------------------------------- screenshots

ROW_TOTAL_LABELS = ["thanh tien", "tong so tien", "tong thanh toan", "tong tien", "tong cong", "so tien",
                    "total", "amount"]
DESC_LABELS = ["noi dung", "loi nhan", "dien giai", "loai dich vu", "dich vu", "mo ta", "content", "description"]


# Transaction-history screens (MoMo "Giao dịch gần đây", bank apps): "<text> -80.000đ", "<more text>", "14:11 - 01/11".
HIST_TIME = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s*$")
HIST_MONTH = re.compile(r"^\s*th[aá]ng\s+(\d{1,2})\s*/\s*(\d{4})\s*$", re.I)
HIST_AMOUNT = re.compile(r"([+\-−–])\s?(?:(\d{1,3}(?:[.,]\d{3}){1,3})\s?(?:đ|d|₫|vnd)?|(\d{4,10})\s?(?:đ|d|₫|vnd))\s*$", re.I)
HIST_BALANCE = re.compile(r"s[ốo]\s*d[ưu][^:]*:\s*[\d.,]+\s*\S?", re.I)  # "Số dư Túi: 2.471.829đ" — a balance, not a charge
HIST_PREFIX = re.compile(r"^thanh\s+to[aá]n\s+(?:cho\s+)?", re.I)


def parse_history(rows: list[str], today: date | None = None, report: dict | None = None) -> list[dict] | None:
    """Entries on a transaction-history screenshot, or None if `rows` is not one (fewer than two time lines).

    `report` gets how many entries could not be read, so the review screen can say so instead of dropping them quietly.
    """
    times = sum(bool(HIST_TIME.match(r)) for r in rows)
    if times < 2:
        return None
    today = today or date.today()
    year, entries, cur = today.year, [], None
    for raw in rows:
        if m := HIST_MONTH.match(raw):
            year = int(m.group(2))
            continue
        if m := HIST_TIME.match(raw):
            if cur is not None:
                y = int(m.group(5) or year)
                try:
                    d = date(y, int(m.group(4)), int(m.group(3)))
                except ValueError:
                    d = None
                if d and d > today:  # no month header on screen and the date belongs to last year
                    d = d.replace(year=y - 1)
                cur["date"] = d.isoformat() if d else None
                entries.append(cur)
            cur = None  # anything until the next amount (e.g. "Tổng tiền lời tháng 11") belongs to no entry
            continue
        row = HIST_BALANCE.sub("", raw).strip()
        if m := HIST_AMOUNT.search(row):
            cur = {"sign": m.group(1), "amount": int(re.sub(r"[.,]", "", m.group(2) or m.group(3))),
                   "text": [row[:m.start()].strip()]}
        elif cur is not None and row:
            cur["text"].append(row)
    out = []
    for e in entries:
        if not e["date"] or e["amount"] < 1000:
            continue  # interest of a few hundred đồng is not worth a row
        desc = HIST_PREFIX.sub("", " ".join(t for t in e["text"] if t)).strip()
        money_in = e["sign"] == "+"  # offered unticked as income: a refund or a salary is not an expense
        out.append({"date": e["date"], "amount": e["amount"], "description": desc, "selected": not money_in,
                    "kind": "income" if money_in else "expense"})
    if report is not None:
        small = sum(1 for e in entries if e["amount"] < 1000)
        report["unreadable"] = max(0, times - len(entries))  # a time line with no amount above it
        report["cut_off"] = 1 if cur is not None else 0      # an amount with no time line: cut by the screen edge
        report["tiny"] = small
    return out


# Where the money came from, read off the screenshot. Order matters: a labelled "Nguồn tiền" line beats app cues,
# and app cues beat a bank name, because "(Techcombank)" after a payee is the receiver's bank, not yours.
SOURCE_LABELS = ("nguon tien", "tai khoan nguon", "tu tai khoan", "the nguon", "thanh toan bang", "phuong thuc thanh toan")
WALLETS = [("Ví MoMo", r"\bmomo\b|tui than tai|so du tui"), ("Ví ZaloPay", r"\bzalo ?pay\b"),
           ("Ví ShopeePay", r"\bshopee ?pay\b"), ("Ví VNPay", r"\bvnpay\b"), ("Viettel Money", r"\bviettel ?money\b")]
BANKS = [("Vietcombank", r"\bvietcombank\b|\bvcb\b"), ("Techcombank", r"\btechcombank\b|\btcb\b"),
         ("MB Bank", r"\bmb ?bank\b"), ("ACB", r"\bacb\b"), ("BIDV", r"\bbidv\b"), ("VietinBank", r"\bvietinbank\b"),
         ("VPBank", r"\bvpbank\b"), ("TPBank", r"\btpbank\b"), ("Sacombank", r"\bsacombank\b"), ("HDBank", r"\bhdbank\b"),
         ("VIB", r"\bvib\b"), ("Agribank", r"\bagribank\b"), ("SHB", r"\bshb\b"), ("MSB", r"\bmsb\b"),
         ("OCB", r"\bocb\b"), ("SeABank", r"\bseabank\b"), ("Timo", r"\btimo\b"), ("Cake", r"\bcake\b")]


def _named(text: str) -> str | None:
    n = normalize(text)
    if re.search(r"\btien mat\b|\bcash\b", n):
        return "Tiền mặt"
    for name, rx in WALLETS + BANKS:
        if re.search(rx, n):
            return name
    return None


def detect_source(rows: list[str]) -> str | None:
    for i, row in enumerate(rows):
        n = normalize(row)
        if any(n.startswith(lbl) for lbl in SOURCE_LABELS):
            value = row.split(":", 1)[1] if ":" in row else (rows[i + 1] if i + 1 < len(rows) else "")
            if found := _named(value) or _named(row):
                return found
    for row in rows[:3]:  # a bank app puts its name alone in the title bar; a payee line is longer
        n = normalize(row)
        if "(" in row or len(n.split()) > 3:
            continue
        for name, rx in BANKS:
            if re.search(rx, n):
                return name
    # "Nội dung: chuyen tien MoMo" on a bank receipt says nothing about where the money came from.
    text = normalize(" ".join(r for r in rows if not normalize(r).startswith(tuple(DESC_LABELS))))
    for name, rx in WALLETS:
        if re.search(rx, text):
            return name
    return None


INCOME_RECEIPT = ("nhan tien", "tien vao", "da nhan", "nhan chuyen khoan", "hoan tien")
NOT_TOTAL = ("khach dua", "tien thua", "tien khach", "giam gia", "chiet khau", "tiet kiem", "so du", "uu dai")


def parse_ocr_rows(rows: list[str], report: dict | None = None) -> list[dict]:
    source = detect_source(rows)
    return [{**c, "pay_account": c.get("pay_account") or source} if source else c
            for c in _parse_ocr_rows(rows, report)]


def _parse_ocr_rows(rows: list[str], report: dict | None = None) -> list[dict]:
    """Candidates from one screenshot. Each has a `selected` guess the user confirms in the app."""
    history = parse_history(rows, report=report)
    if history is not None:
        return history
    found_date = receipt_date(rows)
    guessed = found_date is None  # shown highlighted in the review: today is a guess, not something on the screen
    found_date = found_date or date.today().isoformat()
    text = normalize(" ".join(rows[:6]))
    kind = "income" if any(w in text for w in INCOME_RECEIPT) else "expense"
    candidates = []

    # 1) Labelled totals — one per order on a Shopee/TikTok "Đơn mua" list, one on a bank receipt.
    for i, row in enumerate(rows):
        norm = normalize(row)
        if not any(lbl in norm for lbl in ROW_TOTAL_LABELS):
            continue
        money = find_money(row) or (find_money(rows[i + 1]) if i + 1 < len(rows) else [])
        if not money:
            continue
        candidates.append({"date": found_date, "amount": money[-1][0],
                           "description": _describe(rows, i), "selected": True})

    # 2) Nothing labelled: offer every amount, preselect the largest that is not cash handed over, change or a discount.
    if not candidates:
        for i, row in enumerate(rows):
            for value, _ in find_money(row):
                candidates.append({"date": found_date, "amount": value, "description": _describe(rows, i),
                                   "selected": False, "_skip": any(w in normalize(row) for w in NOT_TOTAL)})
        pickable = [c for c in candidates if not c["_skip"]]
        if pickable:
            max(pickable, key=lambda c: c["amount"])["selected"] = True
        for c in candidates:
            del c["_skip"]
    for c in candidates:
        c["kind"] = kind
        if guessed:
            c["date_guessed"] = True

    seen, unique = set(), []
    for c in candidates:
        key = (c["amount"], c["description"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _describe(rows: list[str], i: int) -> str:
    for lbl in DESC_LABELS:  # a "Nội dung: ..." line beats anything nearby; earlier labels win
        for row in rows:
            if normalize(row).startswith(lbl):
                # normalize() keeps one char per precomposed Vietnamese letter, so the label length carries over
                return row[len(lbl):].lstrip(" :").strip() or row
    # Otherwise the nearest price-free text line above the amount (product or shop name).
    for j in range(i - 1, max(-1, i - 6), -1):
        row = rows[j]
        if len(row) >= 6 and not find_money(row) and re.search(r"[A-Za-zÀ-ỹ]{3}", row):
            return row
    return ""


def email_datetime(header_date: str | None) -> str:
    """Local ISO timestamp. Keep the time: same-day emails (placed, then shipped) must sort in order."""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(header_date).astimezone().isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return datetime.now().isoformat(timespec="seconds")
