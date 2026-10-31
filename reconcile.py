"""Match statement lines to app transactions. User decisions (ignore / manual link / added) are kept;
everything else is re-matched on every run, so new Gmail or manual entries are picked up."""
import sqlite3
from datetime import date

from rules import normalize

DATE_WINDOW = 3      # card posting date lags the purchase by 1–3 days
EXACT_TOLERANCE = 1_000
NEAR_PCT = 0.15      # tips, FX fees, shipping changes


def _days(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def _similarity(a: str, b: str) -> float:
    wa = {w for w in normalize(a).split() if len(w) >= 3}
    wb = {w for w in normalize(b).split() if len(w) >= 3}
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


def match(lines: list[dict], txs: list[dict], account: str = "") -> dict[int, dict]:
    """Greedy one-to-one: same kind, amount within EXACT_TOLERANCE, closest date first."""
    pairs = []
    for ln in lines:
        for t in txs:
            if t["kind"] != ln["kind"] or abs(t["amount"] - ln["amount"]) > EXACT_TOLERANCE:
                continue
            dd = _days(t["date"], ln["date"])
            if dd <= DATE_WINDOW:
                same_card = bool(account) and (t.get("pay_account") or "") == account
                pairs.append((dd, not same_card, -_similarity(ln["description"], t["description"]), ln["id"], t["id"]))
    pairs.sort()
    by_tx = {t["id"]: t for t in txs}
    used_lines, used_tx, out = set(), set(), {}
    for *_, lid, tid in pairs:
        if lid not in used_lines and tid not in used_tx:
            used_lines.add(lid)
            used_tx.add(tid)
            out[lid] = by_tx[tid]
    return out


def suggest(line: dict, txs: list[dict]) -> dict | None:
    """Closest transaction that is *almost* the same: same kind, within the date window, amount within NEAR_PCT."""
    best = None
    for t in txs:
        if t["kind"] != line["kind"] or _days(t["date"], line["date"]) > DATE_WINDOW:
            continue
        diff = abs(t["amount"] - line["amount"])
        if 0 < diff <= line["amount"] * NEAR_PCT:
            key = (diff, _days(t["date"], line["date"]))
            if best is None or key < best[0]:
                best = (key, t)
    return best[1] if best else None


def run(conn: sqlite3.Connection, statement_id: int) -> dict:
    st = conn.execute("SELECT * FROM statements WHERE id = ?", (statement_id,)).fetchone()
    if not st:
        raise KeyError(statement_id)
    lines = [dict(r) for r in conn.execute("SELECT * FROM statement_lines WHERE statement_id = ? ORDER BY date, id",
                                           (statement_id,))]
    if not lines:
        return {"statement": dict(st), "summary": {}, "matched": [], "missing": [], "ignored": [],
                "only_app_card": [], "only_app_other": []}
    first, last = min(l["date"] for l in lines), max(l["date"] for l in lines)
    txs = [dict(r) for r in conn.execute(
        "SELECT t.*, c.name AS category, c.icon AS icon FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
        "WHERE t.status = 'ok' AND t.date BETWEEN date(?, ?) AND date(?, ?)",
        (first, f"-{DATE_WINDOW} days", last, f"+{DATE_WINDOW} days"))]
    by_id = {t["id"]: t for t in txs}

    kept = {l["match_tx_id"] for l in lines if l["status"] in ("manual", "added") and l["match_tx_id"]}
    pending = [l for l in lines if l["status"] in (None, "auto")]
    free = [t for t in txs if t["id"] not in kept]
    auto = match(pending, free, st["account"])
    for l in pending:
        t = auto.get(l["id"])
        conn.execute("UPDATE statement_lines SET status = ?, match_tx_id = ? WHERE id = ?",
                     ("auto" if t else None, t["id"] if t else None, l["id"]))
        l["status"], l["match_tx_id"] = ("auto", t["id"]) if t else (None, None)

    matched_ids = {l["match_tx_id"] for l in lines if l["match_tx_id"]}
    unmatched_tx = [t for t in txs if t["id"] not in matched_ids]
    matched, missing, ignored = [], [], []
    for l in lines:
        if l["status"] == "ignored":
            ignored.append(l)
        elif l["match_tx_id"] and l["match_tx_id"] in by_id:
            matched.append({"line": l, "tx": by_id[l["match_tx_id"]], "how": l["status"]})
        else:
            s = suggest(l, unmatched_tx)
            missing.append({"line": l, "suggestion": s})

    suggested = {m["suggestion"]["id"] for m in missing if m["suggestion"]}  # already shown next to its line
    in_period = [t for t in unmatched_tx if first <= t["date"] <= last and t["kind"] == "expense"
                 and t["source"] != "statement" and t["id"] not in suggested]
    on_card = [t for t in in_period if st["account"] and (t.get("pay_account") or "") == st["account"]]
    other = [t for t in in_period if t not in on_card]
    debit = [l for l in lines if l["kind"] == "expense" and l["status"] != "ignored"]
    summary = {
        "first": first, "last": last, "lines": len(lines),
        "debit_count": len(debit), "debit_total": sum(l["amount"] for l in debit),
        "matched_count": len(matched), "matched_total": sum(m["line"]["amount"] for m in matched),
        "missing_count": len(missing), "missing_total": sum(m["line"]["amount"] for m in missing if m["line"]["kind"] == "expense"),
        "near_count": sum(1 for m in missing if m["suggestion"]),
        "ignored_count": len(ignored),
        "only_card_count": len(on_card), "only_card_total": sum(t["amount"] for t in on_card),
    }
    return {"statement": dict(st), "summary": summary, "matched": matched, "missing": missing, "ignored": ignored,
            "only_app_card": on_card, "only_app_other": other}
