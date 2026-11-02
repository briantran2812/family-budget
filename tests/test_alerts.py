from datetime import date

import pytest

import alerts
import db

TODAY = date(2026, 11, 15)


def cat_id(conn, name, budget=None):
    cid = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()[0]
    if budget:
        conn.execute("UPDATE categories SET budget = ? WHERE id = ?", (budget, cid))
    return cid


def spend(conn, cid, amount, day="2026-11-10", status="ok", kind="expense"):
    conn.execute("INSERT INTO transactions(date, amount, kind, description, category_id, status) "
                 "VALUES (?, ?, ?, 'x', ?, ?)", (day, amount, kind, cid, status))


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(alerts, "notify", out.append)
    return out


@pytest.mark.parametrize("amount, level", [(799_000, None), (800_000, "warn"), (1_000_000, "warn"),
                                           (1_001_000, "over")])
def test_thresholds(conn, amount, level):
    spend(conn, cat_id(conn, "Học phí", 1_000_000), amount)
    got = alerts.budget_alerts(conn, "2026-11")
    assert [a["level"] for a in got] == ([level] if level else [])


def test_exactly_80_percent_of_an_awkward_budget(conn):
    spend(conn, cat_id(conn, "Học phí", 2_000_000), 1_600_000)
    spend(conn, cat_id(conn, "Điện nước", 3_000_000), 2_399_999)
    assert [a["name"] for a in alerts.budget_alerts(conn, "2026-11")] == ["Học phí"]


def test_no_budget_cancelled_income_and_other_months_ignored(conn):
    spend(conn, cat_id(conn, "Khác"), 9_000_000)                       # no budget
    cid = cat_id(conn, "Học phí", 1_000_000)
    spend(conn, cid, 900_000, status="cancelled")
    spend(conn, cid, 900_000, kind="income")
    spend(conn, cid, 900_000, day="2026-10-31")
    spend(conn, cid, 900_000, day="2026-12-01")
    assert alerts.budget_alerts(conn, "2026-11") == []
    spend(conn, cid, 850_000)
    [a] = alerts.budget_alerts(conn, "2026-11")
    assert (a["amount"], a["pct"], a["level"]) == (850_000, 85, "warn")


def test_messages():
    a = {"icon": "🛒", "name": "Ăn uống & đi chợ", "budget": 2_000_000, "amount": 1_700_000, "level": "warn"}
    assert alerts.message(a) == "🛒 Ăn uống & đi chợ đã dùng 85% ngân sách tháng (1,7 tr / 2 tr) — còn 300k"
    a.update(amount=2_250_000, level="over")
    assert alerts.message(a) == "🛒 Ăn uống & đi chợ đã vượt ngân sách tháng 250k (2,3 tr / 2 tr)"
    a.update(amount=1_999_000, level="warn")
    assert "đã dùng 99%" in alerts.message(a)  # rounded down: not yet a full 100%


def test_crossing_80_then_100_notifies_once_each(conn, sent):
    cid = cat_id(conn, "Học phí", 1_000_000)
    spend(conn, cid, 700_000)
    assert alerts.notify_crossings(conn, TODAY) == []
    spend(conn, cid, 150_000)
    alerts.notify_crossings(conn, TODAY)
    alerts.notify_crossings(conn, TODAY)
    assert len(sent) == 1 and "đã dùng 85%" in sent[0]
    spend(conn, cid, 100_000)                                   # 95%: still the same threshold
    assert alerts.notify_crossings(conn, TODAY) == []
    spend(conn, cid, 100_000)
    alerts.notify_crossings(conn, TODAY)
    alerts.notify_crossings(conn, TODAY)
    assert len(sent) == 2 and "vượt ngân sách tháng 50k" in sent[1]


def test_jumping_past_100_sends_one_over_message(conn, sent):
    spend(conn, cat_id(conn, "Học phí", 1_000_000), 1_500_000)
    alerts.notify_crossings(conn, TODAY)
    assert len(sent) == 1 and "vượt" in sent[0]


def test_raising_the_budget_then_crossing_again_stays_quiet(conn, sent):
    cid = cat_id(conn, "Học phí", 1_000_000)
    spend(conn, cid, 900_000)
    alerts.notify_crossings(conn, TODAY)
    conn.execute("UPDATE categories SET budget = 2000000 WHERE id = ?", (cid,))
    alerts.notify_crossings(conn, TODAY)
    spend(conn, cid, 800_000)                                   # 85% of the new budget
    alerts.notify_crossings(conn, TODAY)
    assert len(sent) == 1
    alerts.notify_crossings(conn, date(2026, 12, 1))            # a new month starts fresh
    spend(conn, cid, 1_700_000, day="2026-12-02")
    alerts.notify_crossings(conn, date(2026, 12, 2))
    assert len(sent) == 2


def test_past_month_spending_does_not_notify(conn, sent):
    spend(conn, cat_id(conn, "Học phí", 1_000_000), 5_000_000, day="2026-10-05")
    assert alerts.notify_crossings(conn, TODAY) == []
    assert not conn.execute("SELECT 1 FROM settings WHERE key LIKE 'alert:%'").fetchone()


def test_notify_escapes_quotes_and_never_raises(monkeypatch):
    calls = []
    monkeypatch.setattr(alerts.subprocess, "run", lambda argv, **kw: calls.append(argv))
    alerts.notify('Mua "son" \\ kem')
    assert calls == [["osascript", "-e",
                      'display notification "Mua \\"son\\" \\\\ kem" with title "Thu Chi Gia Đình"']]

    def missing(*a, **kw):
        raise FileNotFoundError("osascript")
    monkeypatch.setattr(alerts.subprocess, "run", missing)
    alerts.notify("x")


# ---------------------------------------------------------------- through the API

def budget(api, name, amount):
    cid = next(c["id"] for c in api.get("/api/categories").json if c["name"] == name)
    api.patch(f"/api/categories/{cid}", json={"budget": amount})
    return cid


def test_summary_lists_alerts(api):
    month = date.today().strftime("%Y-%m")
    budget(api, "Học phí", 1_000_000)
    api.post("/api/transactions", json={"date": f"{month}-01", "amount": 850_000, "description": "Học phí"})
    [a] = api.get(f"/api/summary?month={month}").json["alerts"]
    assert (a["name"], a["level"], a["amount"], a["budget"]) == ("Học phí", "warn", 850_000, 1_000_000)


@pytest.fixture
def desktop(monkeypatch, sent):
    from app import app
    monkeypatch.setitem(app.config, "DESKTOP", True)
    return sent


def test_writes_notify_only_in_the_window_and_only_for_this_month(api, sent, monkeypatch):
    month = date.today().strftime("%Y-%m")
    budget(api, "Học phí", 1_000_000)
    api.post("/api/transactions", json={"date": f"{month}-01", "amount": 900_000, "description": "Học phí"})
    assert sent == []                                            # browser mode / tests: no notifications
    from app import app
    monkeypatch.setitem(app.config, "DESKTOP", True)
    api.post("/api/transactions", json={"date": "2020-01-15", "amount": 5_000_000, "description": "Học phí"})
    assert len(sent) == 1 and "90%" in sent[0]                   # the first write in the window catches up
    api.post("/api/transactions", json={"date": "2020-01-16", "amount": 5_000_000, "description": "Học phí"})
    assert len(sent) == 1
    with db.connect() as c:
        assert not c.execute("SELECT 1 FROM settings WHERE key LIKE 'alert:2020-%'").fetchone()


def test_budget_change_notifies_and_a_failure_does_not_break_the_write(api, desktop, monkeypatch):
    month = date.today().strftime("%Y-%m")
    api.post("/api/transactions", json={"date": f"{month}-01", "amount": 900_000, "description": "Học phí"})
    assert desktop == []
    budget(api, "Học phí", 800_000)                              # lowering the budget is a crossing too
    assert len(desktop) == 1 and "vượt" in desktop[0]

    def boom(conn):
        raise RuntimeError("disk full")
    monkeypatch.setattr(alerts, "notify_crossings", boom)
    r = api.post("/api/transactions", json={"date": f"{month}-02", "amount": 1, "description": "x"})
    assert r.status_code == 200
