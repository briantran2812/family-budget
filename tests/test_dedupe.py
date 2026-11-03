"""The same payment arriving twice: an email and a typed entry, or two people typing it. dedupe.py, via the real paths."""
import gmail_sync
import phone_inbox
import rules
from test_phone_inbox import CODE


def momo_email(conn, amount, received, txid="123456789012", service="Tiền điện EVN HCMC"):
    body = f"Giao dịch thành công\nDịch vụ\n{service}\nSố tiền\n{amount:,}đ\nMã giao dịch: {txid}".replace(",", ".")
    return gmail_sync.process(conn, rules.load(conn), f"<{txid}>", received, "MoMo <no-reply@momo.vn>",
                              "Giao dịch thành công", body)


def inbox_row(rid, amount, desc="Tiền điện tháng 10", time="2026-11-03T09:00:00", account="Ví MoMo",
              by="iPhone của Vy", channel="", date=None):
    r = {"id": rid, "time": time, "amount": amount, "description": desc, "account": account, "by": by, "row": 2,
         "channel": channel}
    if date:
        r["date"] = date
    return r


def sync(conn, fake_sheet, *rows):
    if not phone_inbox.connected(conn):
        phone_inbox.connect(conn, CODE)
    fake_sheet["rows"] = list(rows)
    return phone_inbox.sync(conn)


def txs(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM transactions ORDER BY id")]


def counted(conn):
    return conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE status = 'ok'").fetchone()[0]


def test_momo_email_after_typed_entry_is_merged(conn, fake_sheet):
    sync(conn, fake_sheet, inbox_row("a1", 746_855))
    assert momo_email(conn, 746_855, "2026-11-03")[0] == "imported"
    typed, email = txs(conn)
    assert (typed["status"], typed["link_ref"], typed["description"]) == ("ok", "momo:123456789012", "Tiền điện tháng 10")
    assert (email["status"], email["dup_with"], email["pay_account"]) == ("merged", typed["id"], "Ví MoMo")
    assert counted(conn) == 746_855
    assert momo_email(conn, 746_855, "2026-11-03")[0] == "duplicate"  # the same email read again


def test_typed_entry_after_momo_email_is_merged_and_keeps_the_typed_words(conn, fake_sheet):
    momo_email(conn, 746_855, "2026-11-02")
    sync(conn, fake_sheet, inbox_row("a1", 746_855, date="2026-11-03", account=""))
    email, typed = txs(conn)
    assert (email["status"], typed["status"], typed["description"]) == ("merged", "ok", "Tiền điện tháng 10")
    assert typed["pay_account"] == "Ví MoMo"  # learnt from the email when the entry had none
    assert counted(conn) == 746_855


def test_momo_email_never_matches_a_cash_entry(conn, fake_sheet):
    sync(conn, fake_sheet, inbox_row("a1", 45_000, "Phở", account="Tiền mặt"))
    momo_email(conn, 45_000, "2026-11-03", service="Phở Hòa")
    assert [t["status"] for t in txs(conn)] == ["ok", "ok"] and counted(conn) == 90_000


def test_window_typed_up_to_three_days_late_or_one_day_early(conn, fake_sheet):
    momo_email(conn, 100_000, "2026-11-01", txid="111111111111")
    momo_email(conn, 200_000, "2026-11-01", txid="222222222222")
    momo_email(conn, 300_000, "2026-11-02", txid="333333333333")
    sync(conn, fake_sheet, inbox_row("late", 100_000, date="2026-11-04"),     # 3 days after: same payment
         inbox_row("too-late", 200_000, date="2026-11-05"),                   # 4 days after: another one
         inbox_row("early", 300_000, date="2026-11-01"))                      # typed with yesterday's date
    by_amount = {t["amount"]: t["status"] for t in txs(conn) if t["source"] == "momo"}
    assert by_amount == {100_000: "merged", 200_000: "ok", 300_000: "merged"}


def test_email_matching_two_typed_entries_waits_for_the_user(conn, fake_sheet, api):
    sync(conn, fake_sheet, inbox_row("a1", 45_000, "Phở", by="Telegram · Brian", channel="telegram"),
         inbox_row("a2", 45_000, "Bún bò", by="iPhone của Vy"))
    conn.commit()
    momo_email(conn, 45_000, "2026-11-03", service="Phở Hòa")
    email = txs(conn)[-1]
    assert (email["status"], email["dup_state"]) == ("cancelled", "open")  # out of the totals until answered
    assert counted(conn) == 90_000
    conn.commit()
    note = api.get("/api/notifications").json["items"][0]
    assert note["title"].startswith("Có thể trùng: 45.000 ₫") and note["link"] == {"tx": email["id"]}
    cands = api.get(f"/api/transactions/{email['id']}/dup").json
    assert len(cands) == 2 and "Phở" in cands[0]["text"] + cands[1]["text"]
    bun = next(t for t in txs(conn) if t["description"] == "Bún bò")
    assert api.post(f"/api/transactions/{email['id']}/dup", json={"action": "merge", "other": bun["id"]}).status_code == 200
    got = {t["id"]: t for t in api.get("/api/transactions?month=2026-11").json}
    assert email["id"] not in got  # a merged email row is not listed
    assert got[bun["id"]]["link_ref"] == "momo:123456789012"
    assert sum(t["amount"] for t in got.values() if t["status"] == "ok") == 90_000


def test_two_people_typing_the_same_payment_are_flagged_not_merged(conn, fake_sheet, api):
    sync(conn, fake_sheet, inbox_row("a1", 127_000, "Đi chợ", by="Telegram · Brian", channel="telegram", account="Tiền mặt"),
         inbox_row("a2", 127_000, "Chợ sáng", by="iPhone của Vy", account="Tiền mặt"))
    a, b = txs(conn)
    assert (a["dup_state"], b["dup_state"], b["dup_with"]) == ("open", "open", a["id"])
    assert counted(conn) == 254_000  # both count until someone answers
    conn.commit()
    api.post(f"/api/transactions/{b['id']}/dup", json={"action": "drop"})
    a, b = txs(conn)
    assert (a["status"], b["status"], a["dup_state"], b["dup_state"]) == ("ok", "cancelled", "kept", "kept")


def test_same_person_same_channel_twice_is_not_flagged(conn, fake_sheet):
    sync(conn, fake_sheet, inbox_row("a1", 45_000, "Cà phê", by="iPhone của Vy", account="Tiền mặt"),
         inbox_row("a2", 45_000, "Cà phê", by="iPhone của Vy", account="Tiền mặt"))
    assert [t["dup_state"] for t in txs(conn)] == [None, None]


def test_mac_form_entry_is_checked_too(conn, api, fake_sheet):
    sync(conn, fake_sheet, inbox_row("a1", 60_000, "Ăn sáng bún bò", by="Telegram · Brian", channel="telegram",
                                     account="Tiền mặt"))
    conn.commit()
    r = api.post("/api/transactions", json={"date": "2026-11-03", "amount": 60_000, "description": "Bún bò"})
    assert r.json["flagged"] == 1


def test_keep_both_from_telegram_clears_the_flag(conn, fake_sheet):
    rows = [inbox_row("a1", 127_000, by="Telegram · Brian", channel="telegram", account="Tiền mặt"),
            inbox_row("a2", 127_000, by="iPhone của Vy", account="Tiền mặt")]
    sync(conn, fake_sheet, *rows)
    fake_sheet["kept"] = ["a2"]
    sync(conn, fake_sheet, *rows)
    assert [t["dup_state"] for t in txs(conn)] == ["kept", "kept"]


def test_split_undoes_a_merge_for_good(conn, fake_sheet, api):
    sync(conn, fake_sheet, inbox_row("a1", 746_855))
    momo_email(conn, 746_855, "2026-11-03")
    typed, email = txs(conn)
    conn.commit()
    api.post(f"/api/transactions/{typed['id']}/dup", json={"action": "split"})
    typed, email = txs(conn)
    assert (typed["status"], email["status"], typed["link_ref"]) == ("ok", "ok", None)
    assert counted(conn) == 2 * 746_855
    sync(conn, fake_sheet, inbox_row("a1", 746_855))  # a later sync does not merge them again
    assert [t["status"] for t in txs(conn)] == ["ok", "ok"]


def test_cancelled_order_email_cancels_the_typed_entry_it_was_merged_into(conn, fake_sheet):
    from test_gmail_sync import shopee
    sync(conn, fake_sheet, inbox_row("a1", 465_000, "Kem chống nắng", account=""))
    stamp, mid, sender, subject, body = shopee("261103ABCD1234", 465_000, "2026-11-03")
    gmail_sync.process(conn, rules.load(conn), mid, stamp, sender, subject, body)
    assert [t["status"] for t in txs(conn)] == ["ok", "merged"]
    gmail_sync.process(conn, rules.load(conn), "<c>", "2026-11-04", sender, "Đơn hàng #261103ABCD1234 đã hủy", "Đã hủy")
    assert counted(conn) == 0


def test_deleting_the_typed_entry_brings_the_email_back(conn, fake_sheet, api):
    sync(conn, fake_sheet, inbox_row("a1", 746_855))
    momo_email(conn, 746_855, "2026-11-03")
    typed, email = txs(conn)
    conn.commit()
    api.delete(f"/api/transactions/{typed['id']}")
    [left] = txs(conn)
    assert (left["id"], left["status"], left["dup_with"]) == (email["id"], "ok", None)


def test_mirror_leaves_merged_rows_out(conn, fake_sheet):
    sync(conn, fake_sheet, inbox_row("a1", 746_855))
    momo_email(conn, 746_855, "2026-11-03")
    assert len(phone_inbox.mirror_payload(conn)["rows"]) == 1


def test_wallet_reading():
    import dedupe
    assert [dedupe.wallet(p) for p in ("Ví MoMo", "momo", "Tiền mặt", "TM", "Thẻ Visa", "", None, "ZaloPay")] == \
        ["momo", "momo", "cash", "cash", "other", None, None, "zalopay"]
