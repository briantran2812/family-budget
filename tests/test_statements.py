import pytest

import statements
from samples import statement_csv, statement_pdf, statement_xlsx

ROWS = [
    ("2026-10-03", "HIGHLANDS COFFEE Q1 HCM", 65_000, "expense"),
    ("2026-10-05", "SHOPEE PAY *ORDER 261005", 465_000, "expense"),
    ("2026-10-12", "GOGI HOUSE VINCOM", 1_350_000, "expense"),
    ("2026-10-15", "THANH TOAN THE - CAM ON", 5_000_000, "income"),
    ("2026-10-20", "HOAN TIEN SHOPEE", 120_000, "income"),
]


@pytest.mark.parametrize("text,want", [
    ("1,250,000", (1250000, None)), ("1.250.000", (1250000, None)), ("1,250,000.00", (1250000, None)),
    ("1.250.000,00", (1250000, None)), ("-350.000", (350000, "neg")), ("(120,000)", (120000, "neg")),
    ("2,000,000 CR", (2000000, "cr")), ("65000", (65000, None)), ("99,90", (100, None)),
    (1350000, (1350000, None)), (-50000.0, (50000, "neg")), ("", None), ("abc", None), (None, None), ("0", None),
])
def test_parse_amount(text, want):
    assert statements.parse_amount(text) == want


@pytest.mark.parametrize("text,hint,want", [
    ("05/10/2026", None, "2026-10-05"), ("05-10-26", None, "2026-10-05"), ("2026-10-05", None, "2026-10-05"),
    ("05/10", 2026, "2026-10-05"), ("05/10", None, None), ("05 Oct 2026", None, "2026-10-05"),
    ("05-OCT-26", None, "2026-10-05"), ("31/02/2026", None, None), ("Số dư", None, None),
])
def test_parse_date(text, hint, want):
    assert statements.parse_date(text, hint) == want


def _summary(lines):
    return [(l["date"], l["amount"], l["kind"], l["ignored"]) for l in lines]


EXPECTED = [("2026-10-03", 65_000, "expense", False), ("2026-10-05", 465_000, "expense", False),
            ("2026-10-12", 1_350_000, "expense", False), ("2026-10-15", 5_000_000, "income", True),
            ("2026-10-20", 120_000, "income", False)]


def test_csv_bank_export_with_preamble_and_balance_row():
    lines = statements.parse_file("saoke.csv", statement_csv(ROWS))
    assert _summary(lines) == EXPECTED
    assert lines[0]["description"] == "HIGHLANDS COFFEE Q1 HCM"


def test_csv_single_signed_amount_column():
    data = "Date;Description;Amount\n03/10/2026;Coffee;-65.000\n05/10/2026;Lương;50.000.000\n".encode()
    lines = statements.parse_file("export.csv", data)
    assert [(l["amount"], l["kind"]) for l in lines] == [(65_000, "expense"), (50_000_000, "income")]


def test_xlsx_card_statement_prefers_vnd_column(tmp_path):
    p = tmp_path / "visa.xlsx"
    statement_xlsx(p, ROWS)
    assert _summary(statements.parse_file(p.name, p.read_bytes())) == EXPECTED


def test_pdf_card_statement(tmp_path):
    p = tmp_path / "visa.pdf"
    statement_pdf(p, ROWS)
    lines = statements.parse_file(p.name, p.read_bytes())
    assert _summary(lines) == EXPECTED  # header, balance and total lines are skipped
    assert lines[2]["description"] == "GOGI HOUSE VINCOM"


def test_pdf_with_password(tmp_path):
    p = tmp_path / "visa.pdf"
    statement_pdf(p, ROWS, password="01011990")
    with pytest.raises(statements.NeedPassword, match="mật khẩu"):
        statements.parse_file(p.name, p.read_bytes())
    with pytest.raises(statements.NeedPassword, match="Sai mật khẩu"):
        statements.parse_file(p.name, p.read_bytes(), "wrong")
    assert len(statements.parse_file(p.name, p.read_bytes(), "01011990")) == 5


@pytest.mark.parametrize("name,data,msg", [
    ("a.xls", b"x", "xlsx"), ("a.docx", b"x", "CSV"), ("a.csv", b"foo,bar\n1,2\n", "tiêu đề"),
])
def test_unsupported_or_unrecognised(name, data, msg):
    with pytest.raises(statements.StatementError, match=msg):
        statements.parse_file(name, data)


def test_pdf_short_descriptions_far_from_amounts(tmp_path):
    """PDFKit's own text order splits such tables into column blocks; rows must be rebuilt from positions."""
    rows = [("2026-10-03", "HIGHLANDS Q1", 65_000, "expense"), ("2026-10-12", "GOGI", 1_350_000, "expense"),
            ("2026-10-18", "CIRCLE K", 89_000, "expense")]
    p = tmp_path / "v.pdf"
    statement_pdf(p, rows)
    got = [(l["date"], l["description"], l["amount"]) for l in statements.parse_file(p.name, p.read_bytes())]
    assert got == [("2026-10-03", "HIGHLANDS Q1", 65_000), ("2026-10-12", "GOGI", 1_350_000),
                   ("2026-10-18", "CIRCLE K", 89_000)]
