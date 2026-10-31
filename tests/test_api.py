import json


def add(api, **t):
    r = api.post("/api/transactions", json=t)
    assert r.status_code == 200, r.json
    return r.json["ids"][0]


def test_guard_rejects_other_hosts_and_missing_header(client):
    assert client.get("/api/info", base_url="http://evil.example").status_code == 403
    assert client.post("/api/transactions", json={}, base_url="http://127.0.0.1:8765").status_code == 403


def test_summary_percentages_and_totals(api):
    add(api, date="2026-10-01", amount=50_000_000, kind="income", description="Lương")
    add(api, date="2026-10-05", amount=6_000_000, description="Học phí")
    add(api, date="2026-10-10", amount=3_000_000, description="Tiền điện EVN")
    add(api, date="2026-10-11", amount=1_000_000, description="Tiền nước")
    add(api, date="2026-09-05", amount=6_000_000, description="Học phí")
    s = api.get("/api/summary?month=2026-10").json
    assert (s["expense"], s["income"], s["count"]) == (10_000_000, 50_000_000, 4)
    cats = {c["name"]: c for c in s["categories"]}
    assert cats["Học phí"]["pct"] == 60 and cats["Điện nước"]["pct"] == 40
    assert cats["Học phí"]["prev"] == 6_000_000
    assert round(sum(c["pct"] for c in s["categories"]), 6) == 100
    assert [t["month"] for t in s["trend"]][-2:] == ["2026-09", "2026-10"] and len(s["trend"]) == 12


def test_cancelled_excluded_from_summary(api):
    tid = add(api, date="2026-10-05", amount=500_000, description="Son kem")
    api.patch(f"/api/transactions/{tid}", json={"status": "cancelled"})
    assert api.get("/api/summary?month=2026-10").json["expense"] == 0


def test_month_boundaries(api):
    add(api, date="2026-12-31", amount=100_000, description="a")
    add(api, date="2027-01-01", amount=200_000, description="b")
    assert api.get("/api/summary?month=2026-12").json["expense"] == 100_000
    assert api.get("/api/summary?month=2027-01").json["expense"] == 200_000


def test_invalid_amount_rejected(api):
    assert api.post("/api/transactions", json={"amount": 0, "description": "x"}).status_code == 400
    assert api.post("/api/transactions", json={"description": "x"}).status_code == 400


def test_rule_learning_recategorizes_existing(api):
    tid = add(api, date="2026-10-05", amount=300_000, description="Cần câu cá Shimano")
    other = add(api, date="2026-10-06", amount=200_000, description="Mồi câu cá loại lớn")
    cats = {c["name"]: c["id"] for c in api.get("/api/categories").json}
    tx = {t["id"]: t for t in api.get("/api/transactions?month=2026-10").json}
    assert tx[other]["category"] == "Khác"
    api.patch(f"/api/transactions/{tid}", json={"category_id": cats["Giải trí & du lịch"]})
    r = api.post("/api/rules", json={"keyword": "câu cá", "category_id": cats["Giải trí & du lịch"],
                                     "apply_existing": True}).json
    assert r["changed"] == 1
    tx = {t["id"]: t for t in api.get("/api/transactions?month=2026-10").json}
    assert tx[other]["category"] == "Giải trí & du lịch"


def test_budget_roundtrip(api):
    cid = next(c["id"] for c in api.get("/api/categories").json if c["name"] == "Mỹ phẩm & làm đẹp")
    api.patch(f"/api/categories/{cid}", json={"budget": 1_000_000})
    add(api, date="2026-10-05", amount=1_200_000, description="Son kem lì")
    cat = next(c for c in api.get("/api/summary?month=2026-10").json["categories"] if c["id"] == cid)
    assert (cat["budget"], cat["amount"]) == (1_000_000, 1_200_000)
    api.patch(f"/api/categories/{cid}", json={"budget": None})
    assert next(c for c in api.get("/api/categories").json if c["id"] == cid)["budget"] is None


def test_delete_category_leaves_transactions_uncategorized(api):
    cid = next(c["id"] for c in api.get("/api/categories").json if c["name"] == "Học phí")
    add(api, date="2026-10-05", amount=100_000, description="Học phí")
    api.delete(f"/api/categories/{cid}")
    [t] = api.get("/api/transactions?month=2026-10").json
    assert t["category_id"] is None
    assert api.get("/api/summary?month=2026-10").json["categories"][0]["name"] == "Chưa phân loại"


def test_csv_export_has_bom_and_vietnamese(api):
    add(api, date="2026-10-05", amount=100_000, description="Học phí bé An")
    r = api.get("/api/export.csv")
    text = r.data.decode("utf-8")
    assert text.startswith("﻿Ngày,") and "Học phí bé An" in text


def test_profile_and_onboarding(api):
    assert api.get("/api/info").json["onboarded"] is False
    api.post("/api/profile", json={"user_name": "Lan", "onboarded": 1})
    info = api.get("/api/info").json
    assert (info["user_name"], info["onboarded"]) == ("Lan", True)


def test_schema_migration_from_v1(tmp_path, monkeypatch):
    """A database created by version 1.0 (no icon/budget columns) opens and gains them."""
    import sqlite3
    import db
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript("CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, "
                      "kind TEXT NOT NULL DEFAULT 'expense', sort INTEGER NOT NULL DEFAULT 0);"
                      "INSERT INTO categories(name) VALUES ('Học phí');")
    old.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init()
    row = db.connect().execute("SELECT icon, budget FROM categories WHERE name = 'Học phí'").fetchone()
    assert (row["icon"], row["budget"]) == ("🎓", None)
