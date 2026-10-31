"""Read bank / Visa statements (CSV, XLSX, PDF — also password-protected PDF) into plain lines.

Every bank lays its export out differently, so columns are found by header name, not position.
A line is {"date": "YYYY-MM-DD", "amount": int VND > 0, "kind": "expense"|"income", "description": str}.
"""
import csv
import io
import re
from datetime import date, datetime
from pathlib import Path

from rules import normalize


class StatementError(Exception):
    pass


class NeedPassword(StatementError):
    pass


# ---------------------------------------------------------------- amounts and dates

def parse_amount(text) -> tuple[int, str | None] | None:
    """'1,250,000.00' / '-350.000' / '(120,000)' / '2.000.000 CR' → (abs VND, "neg" | "cr" | None).

    A minus sign and a CR marker mean different things: banks write money out as negative, card statements
    write charges as positive and payments/refunds as CR."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return (abs(round(text)), "neg" if text < 0 else None) if text else None
    s = str(text).strip()
    credit = bool(re.search(r"\b(cr|có)\s*$", s, re.I))
    negative = s.startswith("-") or (s.startswith("(") and s.endswith(")")) or s.endswith("-")
    s = re.sub(r"(?i)\b(cr|dr|có|nợ|vnd|vnđ)\b|[₫đ()\s+-]", "", s)
    if not re.fullmatch(r"[\d.,]+", s or "x"):
        return None
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        whole, _, frac = s.rpartition(dec)
        whole = re.sub(r"[.,]", "", whole)
        value = float(f"{whole}.{frac}") if len(frac) <= 2 else float(whole + frac)
    else:
        sep = "," if "," in s else "." if "." in s else ""
        parts = s.split(sep) if sep else [s]
        if sep and len(parts) == 2 and len(parts[1]) in (1, 2):  # a decimal part: 12.5 / 99,90
            value = float(f"{parts[0]}.{parts[1]}")
        else:
            value = float("".join(parts))
    value = round(value)
    return (value, "neg" if negative else "cr" if credit else None) if value else None


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE_TOKEN = r"(?:\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[ -](?:[A-Za-z]{3})[ -]\d{2,4})"


def parse_date(value, year_hint: int | None = None) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value or "").strip()
    try:
        if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T].*)?", s):
            y, mo, d = map(int, m.groups())
        elif m := re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?(?:\s.*)?", s):
            d, mo = int(m[1]), int(m[2])
            y = int(m[3]) if m[3] else year_hint
            if y is None:
                return None
            y = y + 2000 if y < 100 else y
        elif m := re.fullmatch(r"(\d{1,2})[ -]([A-Za-z]{3})[ -](\d{2,4})", s):
            d, mo, y = int(m[1]), MONTHS.get(m[2].lower()), int(m[3])
            y = y + 2000 if y < 100 else y
        else:
            return None
        return date(y, mo, d).isoformat()
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- tables (CSV / XLSX)

# Header names, matched on unaccented lowercase text. Earlier entries win.
DATE_HEADERS = ["ngay giao dich", "ngay gd", "transaction date", "trans date", "ngay thuc hien", "ngay", "date"]
DESC_HEADERS = ["noi dung", "dien giai", "mo ta", "chi tiet", "description", "details", "merchant", "remark", "ten giao dich"]
DEBIT_HEADERS = ["ghi no", "phat sinh no", "ps no", "so tien ghi no", "debit", "withdrawal", "so tien chi", "rut"]
CREDIT_HEADERS = ["ghi co", "phat sinh co", "ps co", "so tien ghi co", "credit", "deposit", "so tien nap"]
AMOUNT_HEADERS = ["so tien vnd", "so tien (vnd)", "amount (vnd)", "so tien giao dich", "so tien", "amount", "gia tri"]
CARD_PAYMENT = re.compile(r"(?<!\w)(thanh toan the|thanh toan du no|payment received|payment - thank|tra no the|autopay)(?!\w)")


def _find(headers: list[str], names: list[str], skip: set[int] = frozenset()) -> int | None:
    for name in names:
        for i, h in enumerate(headers):
            if i not in skip and name in h and "nguyen te" not in h and "usd" not in h:
                return i
    return None


def parse_table(rows: list[list]) -> list[dict]:
    header_idx = None
    for i, row in enumerate(rows[:40]):
        norm = [normalize(str(c or "")) for c in row]
        if _find(norm, DATE_HEADERS) is not None and (
                _find(norm, AMOUNT_HEADERS) is not None or _find(norm, DEBIT_HEADERS) is not None):
            header_idx, headers = i, norm
            break
    if header_idx is None:
        raise StatementError("Không tìm thấy dòng tiêu đề có cột Ngày và cột Số tiền / Ghi nợ.")

    c_date = _find(headers, DATE_HEADERS)
    c_desc = _find(headers, DESC_HEADERS, {c_date})
    c_debit = _find(headers, DEBIT_HEADERS, {c_date})
    c_credit = _find(headers, CREDIT_HEADERS, {c_date})
    c_amount = None if c_debit is not None else _find(headers, AMOUNT_HEADERS, {c_date})

    raw = []
    for row in rows[header_idx + 1:]:
        row = list(row) + [None] * len(headers)
        d = parse_date(row[c_date])
        if not d:
            continue  # blank, subtotal and balance rows have no date
        desc = str(row[c_desc] or "").strip() if c_desc is not None else ""
        if c_debit is not None:
            debit, credit = parse_amount(row[c_debit]), parse_amount(row[c_credit]) if c_credit is not None else None
            if debit:
                raw.append((d, debit[0], "expense", desc))
            elif credit:
                raw.append((d, credit[0], "income", desc))
        else:
            amt = parse_amount(row[c_amount])
            if amt:
                raw.append((d, amt[0], amt[1], desc))  # sign decided below
    if c_debit is None:
        # Bank accounts export "money out" as negative; card statements list charges as positive, credits as CR.
        any_negative = any(sign == "neg" for _, _, sign, _ in raw)
        raw = [(d, a, ("expense" if sign == "neg" else "income") if any_negative else
                ("income" if sign == "cr" else "expense"), desc) for d, a, sign, desc in raw]
    return [{"date": d, "amount": a, "kind": k, "description": desc} for d, a, k, desc in raw]


# ---------------------------------------------------------------- PDF

PDF_LINE = re.compile(rf"^(?P<d1>{DATE_TOKEN})\s+(?:(?P<d2>{DATE_TOKEN})\s+)?(?P<desc>.*?)\s+"
                      rf"(?P<amt>-?\(?[\d][\d.,]*\)?)\s*(?P<cr>CR|Cr|cr)?$")
PDF_SKIP = re.compile(r"(?<!\w)(so du|du no|tong cong|tong phat sinh|han thanh toan|ngay sao ke|minimum|closing|opening)(?!\w)")


def _layout_text(page) -> str:
    """Visual rows of a page. page.string() follows PDFKit's column blocks, which split a statement table into
    "all descriptions" then "all amounts"; line selections carry their position, so pieces on the same row
    can be put back together left to right."""
    from Quartz import kPDFDisplayBoxMediaBox
    sel = page.selectionForRect_(page.boundsForBox_(kPDFDisplayBoxMediaBox))
    pieces = []
    for ln in (sel.selectionsByLine() if sel else []):
        b = ln.boundsForPage_(page)
        pieces.append((b.origin.y + b.size.height / 2, b.size.height, b.origin.x, (ln.string() or "").strip()))
    rows: list[list] = []
    for y, h, x, text in sorted(pieces, key=lambda p: -p[0]):  # PDF origin is bottom-left: top row first
        if rows and abs(rows[-1][0] - y) < h * 0.5:
            rows[-1][1].append((x, text))
        else:
            rows.append([y, [(x, text)]])
    return "\n".join(" ".join(t for _, t in sorted(parts)) for _, parts in rows)


def parse_pdf(data: bytes, password: str = "") -> list[dict]:
    from Foundation import NSData
    from Quartz import PDFDocument
    doc = PDFDocument.alloc().initWithData_(NSData.dataWithBytes_length_(data, len(data)))
    if doc is None:
        raise StatementError("File PDF bị hỏng hoặc không đọc được.")
    if doc.isLocked():
        if not password:
            raise NeedPassword("Sao kê có mật khẩu. Nhập mật khẩu (ngân hàng thường dùng ngày sinh hoặc số CMND/CCCD).")
        if not doc.unlockWithPassword_(password):
            raise NeedPassword("Sai mật khẩu PDF. Thử lại.")
    text = "\n".join(_layout_text(doc.pageAtIndex_(i)) for i in range(doc.pageCount()))
    years = [int(y) for y in re.findall(r"\b\d{1,2}[/.-]\d{1,2}[/.-](20\d\d)\b", text)]
    year_hint = max(set(years), key=years.count) if years else date.today().year
    lines = []
    for ln in text.splitlines():
        ln = re.sub(r"\s+", " ", ln).strip()
        m = PDF_LINE.match(ln)
        if not m or PDF_SKIP.search(normalize(ln)):
            continue
        d = parse_date(m["d1"], year_hint)
        amt = parse_amount(m["amt"] + (" CR" if m["cr"] else ""))
        if d and amt:
            lines.append({"date": d, "amount": amt[0], "kind": "income" if amt[1] else "expense",  # CR or minus
                          "description": m["desc"].strip()})
    if not lines:
        raise StatementError("Không đọc được dòng giao dịch nào trong PDF. Hãy thử tải sao kê dạng Excel/CSV.")
    return lines


# ---------------------------------------------------------------- entry point

def parse_file(filename: str, data: bytes, password: str = "") -> list[dict]:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        lines = parse_pdf(data, password)
    elif ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        lines = []
        for ws in wb.worksheets:  # banks sometimes put a cover sheet first
            try:
                lines = parse_table([list(r) for r in ws.iter_rows(values_only=True)])
                break
            except StatementError:
                continue
        if not lines:
            raise StatementError("Không tìm thấy bảng giao dịch trong file Excel.")
    elif ext in (".csv", ".txt"):
        text = data.decode("utf-8-sig", errors="replace")
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t") if text.strip() else csv.excel
        lines = parse_table(list(csv.reader(io.StringIO(text), dialect)))
    elif ext == ".xls":
        raise StatementError("File .xls (Excel cũ) chưa hỗ trợ — mở bằng Excel/Numbers và lưu lại thành .xlsx hoặc .csv.")
    else:
        raise StatementError("Chỉ nhận file CSV, Excel (.xlsx) hoặc PDF.")
    for ln in lines:  # card payments are money moving between your own accounts, not income
        ln["ignored"] = bool(ln["kind"] == "income" and CARD_PAYMENT.search(normalize(ln["description"])))
    return lines
