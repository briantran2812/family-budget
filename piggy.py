"""Ống heo: at each month end, what is left (income − expense) goes in as a record, so savings can be watched growing."""
import calendar
import sqlite3
from datetime import date

import notifications
from alerts import short

OK_TOTALS = ("SELECT COALESCE(SUM(CASE WHEN kind = 'income' THEN amount END), 0), "
             "COALESCE(SUM(CASE WHEN kind = 'expense' THEN amount END), 0) "
             "FROM transactions WHERE status = 'ok' AND substr(date, 1, 7) = ?")


def today() -> date:
    """The server's date. Tests replace this function: the E2E browser clock is frozen, the server's is not."""
    return date.today()


def last_closed(d: date) -> str:
    """The newest month that may be recorded on day `d`: this month on its last day, else the month before."""
    if d.day == calendar.monthrange(d.year, d.month)[1]:
        return f"{d.year}-{d.month:02d}"
    return f"{d.year - (d.month == 1)}-{(d.month - 2) % 12 + 1:02d}"


def label(month: str) -> str:
    return f"{int(month[5:])}/{month[:4]}"


def message(month: str, saved: int) -> str:
    if saved > 0:
        return f"Tháng {label(month)}: bỏ ống heo {short(saved)}"
    if saved < 0:
        return f"Tháng {label(month)} chi vượt thu {short(-saved)} — ống heo vơi đi"
    return f"Tháng {label(month)}: thu vừa đủ chi, ống heo giữ nguyên"


def _snapshot(conn: sqlite3.Connection, month: str) -> tuple[int, int]:
    return tuple(conn.execute(OK_TOTALS, (month,)).fetchone())


def record_due(conn: sqlite3.Connection, day: date | None = None) -> list[str]:
    """Record every closed month not yet in the piggy, oldest first: the app is often closed at month end.

    A month with no income is skipped as incomplete (Shopee orders pulled from Gmail on first connect go back 6 months);
    it would read as the piggy losing the whole month, and is recorded once its income is added.
    """
    upto = last_closed(day or today())
    months = [r[0] for r in conn.execute(
        "SELECT substr(date, 1, 7) AS m FROM transactions WHERE status = 'ok' AND substr(date, 1, 7) <= ? "
        "AND substr(date, 1, 7) NOT IN (SELECT month FROM piggy) "
        "GROUP BY m HAVING SUM(kind = 'income') > 0 ORDER BY m", (upto,))]
    done = []
    for month in months:
        income, expense = _snapshot(conn, month)
        # Two requests opening the app together may both see the month as due; only the one that inserts notifies.
        if conn.execute("INSERT OR IGNORE INTO piggy(month, income, expense, saved) VALUES (?, ?, ?, ?)",
                        (month, income, expense, income - expense)).rowcount:
            notifications.add(conn, "piggy", "🐷", message(month, income - expense), link={"piggy": True},
                              dedupe=f"piggy:{month}")
            done.append(month)
    conn.commit()
    return done


def refresh(conn: sqlite3.Connection, month: str) -> bool:
    """Re-snapshot a recorded month after late entries (a card statement imported the month after)."""
    income, expense = _snapshot(conn, month)
    return bool(conn.execute("UPDATE piggy SET income = ?, expense = ?, saved = ?, "
                             "recorded_at = datetime('now', 'localtime') WHERE month = ?",
                             (income, expense, income - expense, month)).rowcount)


def listing(conn: sqlite3.Connection) -> dict:
    records = []
    for r in conn.execute("SELECT * FROM piggy ORDER BY month DESC").fetchall():
        income, expense = _snapshot(conn, r["month"])
        records.append({"month": r["month"], "income": r["income"], "expense": r["expense"], "saved": r["saved"],
                        "live_saved": income - expense, "recorded_at": r["recorded_at"]})
    saved = [r["saved"] for r in records]
    total = sum(saved)
    return {"records": records, "total": total, "last3": sum(saved[:3]), "last6": sum(saved[:6]),
            "avg": round(total / len(saved)) if saved else 0, "months": len(saved)}
