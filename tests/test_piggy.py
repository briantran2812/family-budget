"""🐷 Ống heo: one snapshot of income − expense per closed month."""
from datetime import date

import notifications
import piggy


def tx(conn, day, amount, kind="expense", status="ok"):
    conn.execute("INSERT INTO transactions(date, amount, kind, description, status) VALUES (?, ?, ?, 'x', ?)",
                 (day, amount, kind, status))


def month(conn, m, income, expense):
    if income:
        tx(conn, f"{m}-05", income, "income")
    if expense:
        tx(conn, f"{m}-10", expense)


def recorded(conn):
    return [tuple(r) for r in conn.execute("SELECT month, income, expense, saved FROM piggy ORDER BY month")]


def test_last_closed_month():
    assert piggy.last_closed(date(2026, 10, 30)) == "2026-09"
    assert piggy.last_closed(date(2026, 10, 31)) == "2026-10"     # the last day counts
    assert piggy.last_closed(date(2026, 1, 15)) == "2025-12"
    assert piggy.last_closed(date(2028, 2, 29)) == "2028-02"      # leap year
    assert piggy.last_closed(date(2027, 2, 28)) == "2027-02"


def test_records_only_closed_months(conn):
    month(conn, "2026-09", 30_000_000, 18_000_000)
    month(conn, "2026-10", 30_000_000, 20_000_000)
    assert piggy.record_due(conn, date(2026, 10, 30)) == ["2026-09"]
    assert recorded(conn) == [("2026-09", 30_000_000, 18_000_000, 12_000_000)]
    assert piggy.record_due(conn, date(2026, 10, 31)) == ["2026-10"]   # on its last day
    assert piggy.record_due(conn, date(2026, 11, 1)) == []             # already in
    assert len(recorded(conn)) == 2


def test_catches_up_missed_months_and_skips_empty_ones(conn):
    month(conn, "2026-05", 25_000_000, 20_000_000)
    month(conn, "2026-07", 25_000_000, 21_000_000)                    # June: nothing at all
    month(conn, "2026-08", 0, 4_000_000)                               # only Shopee orders from Gmail: no income
    tx(conn, "2026-09-03", 2_000_000, status="cancelled")
    month(conn, "2026-10", 26_000_000, 22_000_000)
    assert piggy.record_due(conn, date(2026, 11, 2)) == ["2026-05", "2026-07", "2026-10"]
    tx(conn, "2026-08-01", 25_000_000, "income")                       # its salary entered later
    assert piggy.record_due(conn, date(2026, 11, 2)) == ["2026-08"]


def test_negative_month_and_bell_once(conn):
    month(conn, "2026-09", 20_000_000, 7_500_000)
    month(conn, "2026-10", 20_000_000, 21_200_000)
    piggy.record_due(conn, date(2026, 11, 2))
    piggy.record_due(conn, date(2026, 11, 3))
    conn.execute("DELETE FROM piggy")                                  # even if recorded again, one bell item per month
    piggy.record_due(conn, date(2026, 11, 4))
    items = notifications.listing(conn)["items"]
    assert [i["title"] for i in items] == ["Tháng 10/2026 chi vượt thu 1,2 tr — ống heo vơi đi",
                                           "Tháng 9/2026: bỏ ống heo 12,5 tr"]
    assert {(i["icon"], i["kind"]) for i in items} == {("🐷", "piggy")}
    assert items[0]["link"] == {"piggy": True}
    assert recorded(conn)[1][3] == -1_200_000


def test_snapshot_keeps_value_until_refreshed(conn):
    month(conn, "2026-10", 30_000_000, 17_500_000)
    piggy.record_due(conn, date(2026, 10, 31))
    tx(conn, "2026-10-28", 600_000)                                    # a card statement imported in November
    [r] = piggy.listing(conn)["records"]
    assert (r["saved"], r["live_saved"]) == (12_500_000, 11_900_000)
    assert piggy.refresh(conn, "2026-10")
    [r] = piggy.listing(conn)["records"]
    assert (r["expense"], r["saved"], r["live_saved"]) == (18_100_000, 11_900_000, 11_900_000)
    assert not piggy.refresh(conn, "2026-09")


def test_sums(conn):
    assert piggy.listing(conn) == {"records": [], "total": 0, "last3": 0, "last6": 0, "avg": 0, "months": 0}
    saved = {"2026-03": 5, "2026-04": 6, "2026-05": -2, "2026-06": 8, "2026-07": 4, "2026-08": 10, "2026-09": 3}
    for m, s in saved.items():
        month(conn, m, 20_000_000 + s * 1_000_000, 20_000_000)
    piggy.record_due(conn, date(2026, 10, 1))
    got = piggy.listing(conn)
    assert [r["month"] for r in got["records"]] == sorted(saved, reverse=True)
    assert got["months"] == 7 and got["total"] == 34_000_000
    assert got["last3"] == (3 + 10 + 4) * 1_000_000
    assert got["last6"] == (3 + 10 + 4 + 8 - 2 + 6) * 1_000_000
    assert got["avg"] == round(34_000_000 / 7)


def test_api_records_on_open_and_refresh(api):
    api.post("/api/transactions", json=[
        {"date": "2026-10-01", "amount": 30_000_000, "kind": "income", "description": "Lương"},
        {"date": "2026-10-05", "amount": 17_500_000, "description": "Học phí"}])
    r = api.get("/api/piggy").get_json()                               # conftest: today is 2026-10-31
    assert (r["total"], r["months"], r["records"][0]["month"]) == (12_500_000, 1, "2026-10")
    api.post("/api/transactions", json={"date": "2026-10-30", "amount": 600_000, "description": "Visa"})
    assert api.get("/api/piggy").get_json()["records"][0]["live_saved"] == 11_900_000
    r = api.post("/api/piggy/2026-10/refresh").get_json()
    assert r["total"] == 11_900_000 and r["records"][0]["live_saved"] == 11_900_000
    assert api.post("/api/piggy/2026-09/refresh").status_code == 404
    titles = [i["title"] for i in api.get("/api/notifications").get_json()["items"]]
    assert titles == ["Tháng 10/2026: bỏ ống heo 12,5 tr"]


def test_bell_shows_a_month_that_just_closed(api, monkeypatch):
    api.post("/api/transactions", json={"date": "2026-10-01", "amount": 1_000_000, "kind": "income"})
    monkeypatch.setattr(piggy, "today", lambda: date(2026, 10, 30))
    assert api.get("/api/notifications").get_json()["items"] == []
    monkeypatch.setattr(piggy, "today", lambda: date(2026, 11, 1))
    assert [i["link"] for i in api.get("/api/notifications").get_json()["items"]] == [{"piggy": True}]
