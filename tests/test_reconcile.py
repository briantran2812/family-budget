"""Reconciliation through the API, the way the page drives it."""
import pytest

from samples import statement_csv


def add(api, **t):
    r = api.post("/api/transactions", json=t)
    assert r.status_code == 200, r.json
    return r.json["ids"][0]


def upload(api, rows, account="Visa Techcombank", name="saoke.csv", data=None, password=None):
    import io
    form = {"file": (io.BytesIO(data or statement_csv(rows)), name), "account": account}
    if password is not None:
        form["password"] = password
    return api.post("/api/statements", data=form)


ROWS = [
    ("2026-10-03", "HIGHLANDS COFFEE Q1", 65_000, "expense"),       # typed in by hand, posted 1 day later
    ("2026-10-05", "SHOPEE PAY ORDER", 465_000, "expense"),         # came from Gmail
    ("2026-10-12", "GOGI HOUSE VINCOM", 1_350_000, "expense"),      # typed 1.200.000 (forgot the tip)
    ("2026-10-18", "CIRCLE K NGUYEN HUE", 89_000, "expense"),       # never recorded
    ("2026-10-15", "THANH TOAN THE - CAM ON", 5_000_000, "income"),  # card payment → auto-ignored
]


@pytest.fixture
def scenario(api):
    ids = {
        "coffee": add(api, date="2026-10-02", amount=65_000, description="Cà phê Highlands", pay_account="Visa Techcombank"),
        "shopee": add(api, date="2026-10-05", amount=465_000, description="Kem chống nắng", source="shopee"),
        "gogi": add(api, date="2026-10-12", amount=1_200_000, description="Ăn tối Gogi", pay_account="Visa Techcombank"),
        "typo": add(api, date="2026-10-16", amount=250_000, description="Nhà sách Fahasa", pay_account="Visa Techcombank"),
        "cash": add(api, date="2026-10-17", amount=30_000, description="Gửi xe", pay_account="Tiền mặt"),
    }
    r = upload(api, ROWS)
    assert r.status_code == 200, r.json
    return ids, r.json


def test_summary_buckets(scenario):
    ids, rec = scenario
    s = rec["summary"]
    assert (s["matched_count"], s["missing_count"], s["ignored_count"]) == (2, 2, 1)
    assert s["missing_total"] == 1_350_000 + 89_000
    assert {m["tx"]["id"] for m in rec["matched"]} == {ids["coffee"], ids["shopee"]}
    assert [t["id"] for t in rec["only_app_card"]] == [ids["typo"]]   # said "Visa", not on the statement
    assert [t["id"] for t in rec["only_app_other"]] == [ids["cash"]]  # cash: informational only
    assert [l["description"] for l in rec["ignored"]] == ["THANH TOAN THE - CAM ON"]


def test_near_match_suggestion_and_fix_amount(api, scenario):
    ids, rec = scenario
    gogi = next(m for m in rec["missing"] if m["line"]["amount"] == 1_350_000)
    assert gogi["suggestion"]["id"] == ids["gogi"]
    rec = api.post(f"/api/statement-lines/{gogi['line']['id']}/link",
                   json={"tx_id": ids["gogi"], "use_statement_amount": True}).json
    assert rec["summary"]["matched_count"] == 3
    tx = {t["id"]: t for t in api.get("/api/transactions?month=2026-10").json}
    assert tx[ids["gogi"]]["amount"] == 1_350_000


def test_add_missing_then_undo(api, scenario):
    _, rec = scenario
    ck = next(m for m in rec["missing"] if m["line"]["amount"] == 89_000)["line"]
    rec = api.post(f"/api/statement-lines/{ck['id']}/add").json
    added = next(m for m in rec["matched"] if m["line"]["id"] == ck["id"])
    assert (added["how"], added["tx"]["source"], added["tx"]["pay_account"]) == ("added", "statement", "Visa Techcombank")
    assert api.get("/api/summary?month=2026-10").json["expense"] == 65_000 + 465_000 + 1_200_000 + 250_000 + 30_000 + 89_000
    rec = api.post(f"/api/statement-lines/{ck['id']}/unlink").json
    assert rec["summary"]["missing_count"] == 2
    assert all(t["source"] != "statement" for t in api.get("/api/transactions?month=2026-10").json)


def test_decisions_survive_rerun_and_new_entries_get_matched(api, scenario):
    _, rec = scenario
    sid = rec["statement"]["id"]
    ck = next(m for m in rec["missing"] if m["line"]["amount"] == 89_000)["line"]
    api.post(f"/api/statement-lines/{ck['id']}/ignore")
    # the user later types in the forgotten dinner tip-included amount
    add(api, date="2026-10-13", amount=1_350_000, description="Gogi (bổ sung)", pay_account="Visa Techcombank")
    rec = api.get(f"/api/statements/{sid}").json
    assert rec["summary"]["ignored_count"] == 2
    assert rec["summary"]["missing_count"] == 0


def test_same_amount_twice_matches_by_closest_date(api):
    a = add(api, date="2026-10-01", amount=50_000, description="Cà phê")
    b = add(api, date="2026-10-04", amount=50_000, description="Cà phê")
    rec = upload(api, [("2026-10-04", "COFFEE", 50_000, "expense"), ("2026-10-02", "COFFEE", 50_000, "expense")]).json
    pairs = {m["line"]["date"]: m["tx"]["id"] for m in rec["matched"]}
    assert pairs == {"2026-10-02": a, "2026-10-04": b}


def test_duplicate_file_rejected(api, scenario):
    assert upload(api, ROWS).status_code == 409


def test_password_pdf_flow(api, tmp_path):
    from samples import statement_pdf
    p = tmp_path / "visa.pdf"
    statement_pdf(p, ROWS, password="01011990")
    r = upload(api, None, name="visa.pdf", data=p.read_bytes())
    assert r.status_code == 400 and r.json["need_password"] is True
    assert upload(api, None, name="visa.pdf", data=p.read_bytes(), password="01011990").status_code == 200


def test_gmail_order_merges_into_statement_transaction(api, conn, scenario, monkeypatch, fake_keyring):
    import gmail_sync
    import parsers
    from samples import shopee_email
    _, rec = scenario
    ck = next(m for m in rec["missing"] if m["line"]["amount"] == 89_000)["line"]
    api.post(f"/api/statement-lines/{ck['id']}/add")
    body = parsers.html_to_text(shopee_email("261017ABCD9999", [("Nước giặt Omo", 1, 89_000)], 0, 0))
    status, tid = gmail_sync.process(conn, None, "<o>", "2026-10-17", "Shopee <info@mail.shopee.vn>",
                                     "Xác nhận đơn hàng #261017ABCD9999", body)
    conn.commit()
    assert status == "imported" and tid == next(m for m in api.get(f"/api/statements/{rec['statement']['id']}").json["matched"]
                                                if m["line"]["id"] == ck["id"])["tx"]["id"]
    tx = {t["id"]: t for t in api.get("/api/transactions?month=2026-10").json}[tid]
    assert (tx["source"], tx["description"], tx["pay_account"]) == ("shopee", "Nước giặt Omo", "Visa Techcombank")


def test_pay_account_listed_for_autocomplete(api, scenario):
    assert api.get("/api/accounts").json == ["Tiền mặt", "Visa Techcombank"]
