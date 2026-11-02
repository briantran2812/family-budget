"""Budget alerts: categories at 80% of their monthly budget or more, and a one-time macOS notification per threshold."""
import subprocess
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import db
import notifications

TITLE = "Thu Chi Gia Đình"


def short(n: int) -> str:
    """Same as `short` in index.html: 1700000 → '1,7 tr', 300000 → '300k'."""
    for unit, size in ((" tỷ", 10**9), (" tr", 10**6)):
        if n >= size:
            # toFixed(1) rounds the float's exact value half up (2,25 → 2,3); Decimal(float) keeps that value.
            tenths = str(Decimal(n / size).quantize(Decimal("0.1"), ROUND_HALF_UP))
            return tenths.removesuffix(".0").replace(".", ",") + unit
    return f"{int(n / 1000 + 0.5)}k" if n >= 1000 else str(n)


def budget_alerts(conn, month: str) -> list[dict]:
    rows = conn.execute(
        "SELECT c.id, c.name, c.icon, c.budget, SUM(t.amount) AS amount FROM categories c "
        "JOIN transactions t ON t.category_id = c.id "
        "WHERE c.budget > 0 AND t.status = 'ok' AND t.kind = 'expense' AND substr(t.date, 1, 7) = ? "
        "GROUP BY c.id ORDER BY SUM(t.amount) * 1.0 / c.budget DESC", (month,)).fetchall()
    out = [{"category_id": r["id"], "name": r["name"], "icon": r["icon"], "budget": r["budget"],
            "amount": r["amount"], "pct": r["amount"] * 100 / r["budget"],  # exact; 290k / 1tr * 100 is 28.999…
            "level": "over" if r["amount"] > r["budget"] else "warn"} for r in rows]
    return [a for a in out if a["pct"] >= 80]


def message(a: dict) -> str:
    used = f"({short(a['amount'])} / {short(a['budget'])})"
    if a["level"] == "over":
        return f"{a['icon']} {a['name']} đã vượt ngân sách tháng {short(a['amount'] - a['budget'])} {used}"
    return (f"{a['icon']} {a['name']} đã dùng {a['amount'] * 100 // a['budget']}% ngân sách tháng {used} "
            f"— còn {short(a['budget'] - a['amount'])}")


def _applescript_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(body: str) -> None:
    """Show a macOS notification. Tests replace this function."""
    try:
        subprocess.run(["osascript", "-e", f"display notification {_applescript_str(body)} "
                                           f"with title {_applescript_str(TITLE)}"],
                       check=False, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"notification failed: {e}", file=sys.stderr)


def notify_crossings(conn, today: date | None = None, desktop: bool = False) -> list[str]:
    """Notify once per category, threshold and month; only the current month, so importing old statements stays quiet.

    A key stays set when the budget is raised or spending drops back, so re-crossing in the same month is silent.
    """
    month = (today or date.today()).strftime("%Y-%m")
    sent = []
    for a in budget_alerts(conn, month):
        keys = [f"alert:{month}:{a['category_id']}:{t}" for t in ((80, 100) if a["level"] == "over" else (80,))]
        new = [k for k in keys if not db.get_setting(conn, k)]
        if not new:
            continue
        for k in new:  # jumping straight past 100% sends only the "over" message
            db.set_setting(conn, k, "1")
        sent.append(message(a))
        notifications.add(conn, "budget", "🔴" if a["level"] == "over" else "⚠️", sent[-1],
                          link={"tab": "tx", "cat": a["category_id"]}, dedupe=new[-1])
        if desktop:  # the bell always; a macOS banner only from the app window
            notify(sent[-1])
    conn.commit()
    return sent
