"""Build a demo household in ./demo-data — through the real pipeline, not straight inserts.

Shopee/TikTok orders become fake emails fed to the email parser; MoMo bills become rendered receipt
images fed to macOS OCR. Run:  .venv/bin/python demo_data.py   then
                               BUDGET_DATA=demo-data .venv/bin/python desktop.py
"""
import os
import random
import shutil
import sys
from datetime import date
from pathlib import Path

import argparse

ROOT = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("seed", nargs="?", type=int, default=2026)
ap.add_argument("--months", default="2026-05,2026-06,2026-07,2026-08,2026-09,2026-10")
ap.add_argument("--out", default="demo-data")
ARGS = ap.parse_args()
DEMO = ROOT / ARGS.out
os.environ["BUDGET_DATA"] = str(DEMO)

import db  # noqa: E402  (reads BUDGET_DATA at import)
import gmail_sync  # noqa: E402
import ocr  # noqa: E402
import parsers  # noqa: E402
import rules  # noqa: E402
from samples import BILLS, PRODUCTS, jitter, momo_receipt, shopee_email, tiktok_email  # noqa: E402

MONTHS = ARGS.months.split(",")
# Per-month story so trends are visible: (online orders range, electricity factor, extra cosmetics orders)
PROFILE = {"2026-09": ((4, 6), 1.30, 0),   # hot month: air-con, fewer online orders
           "2026-10": ((9, 12), 0.85, 3)}  # 10.10 sale: many orders, cosmetics over budget
DEFAULT_PROFILE = ((5, 10), 1.0, 0)
SALARY = 50_000_000

# ---------------------------------------------------------------- build

def main() -> None:
    random.seed(ARGS.seed)
    if DEMO.exists():
        shutil.rmtree(DEMO)
    (DEMO / "momo").mkdir(parents=True)
    db.init()
    conn = db.connect()
    db.set_setting(conn, "onboarded", "1")
    from app import VERSION
    db.set_setting(conn, "seen_version", VERSION)
    db.set_setting(conn, "user_name", "Lan")
    budgets = {"Mỹ phẩm & làm đẹp": 1_500_000, "Ăn uống & đi chợ": 7_000_000, "Mẹ & bé": 2_500_000}
    for name, b in budgets.items():
        conn.execute("UPDATE categories SET budget = ? WHERE name = ?", (b, name))

    stats = {"email": {}, "ocr_ok": 0, "ocr_total": 0}
    emails = []
    compiled = rules.load(conn)

    def add_manual(d, amount, kind, desc):
        conn.execute("INSERT INTO transactions(date, amount, kind, description, source, category_id) "
                     "VALUES (?, ?, ?, ?, 'manual', ?)", (d, amount, kind, desc,
                                                          rules.categorize(conn, desc, kind, compiled)))

    for mi, month in enumerate(MONTHS):
        y, m = map(int, month.split("-"))
        last_day = 31 if m in (5, 7, 8, 10) else 30
        if month == "2026-10":
            last_day = 30
        add_manual(f"{month}-05", SALARY, "income", f"Lương tháng {m}")
        for week_day in (3, 10, 17, 24):
            add_manual(f"{month}-{week_day:02d}", jitter(1_400_000, 0.3), "expense", "Đi chợ, thực phẩm tuần")
        add_manual(f"{month}-{random.randint(1, 28):02d}", jitter(450_000, 0.2), "expense", "Đổ xăng xe máy")
        if random.random() < 0.5:
            add_manual(f"{month}-{random.randint(1, 28):02d}", jitter(1_200_000, 0.4), "expense",
                       "Đi ăn nhà hàng cuối tuần")

        (lo, hi), power, extra_beauty = PROFILE.get(month, DEFAULT_PROFILE)
        beauty = [p for p in PRODUCTS if rules.categorize(conn, p[0], "expense", compiled) ==
                  rules.categorize(conn, "my pham", "expense", compiled)]
        # Shopee + TikTok orders as emails
        for i in range(random.randint(lo, hi) + extra_beauty):
            platform = random.choice(["shopee", "shopee", "tiktok"])
            d = date(y, m, random.randint(1, last_day))
            pool = beauty if i >= random.randint(lo, hi) else PRODUCTS  # the extra orders are cosmetics
            items = [(n, random.choice([1, 1, 1, 2]), jitter(p, 0.2))
                     for n, p in random.sample(pool, random.choice([1, 1, 2]))]
            if platform == "shopee":
                oid = f"{d:%y%m%d}{''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ', k=4))}{random.randint(1000, 9999)}"
                body = parsers.html_to_text(shopee_email(oid, items, random.choice([0, 15_000, 22_000]),
                                                         random.choice([0, 0, 20_000, 50_000])))
                sender, subject = "Shopee <info@mail.shopee.vn>", f"Xác nhận đơn hàng #{oid}"
            else:
                oid = str(random.randint(10 ** 17, 10 ** 18 - 1))
                body = tiktok_email(oid, items)
                sender, subject = "TikTok Shop <noreply@shop.tiktok.com>", "Đơn hàng của bạn đã được đặt thành công"
            emails.append((d.isoformat(), f"<demo-{platform}-{oid}@demo>", sender, subject, body))
            # Follow-up emails the real shops send: shipped (same order, again), sometimes a cancellation.
            emails.append((d.isoformat(), f"<demo-ship-{oid}@demo>", sender, f"Đơn hàng #{oid} đang được giao",
                           body))
            if random.random() < 0.08:
                emails.append((d.isoformat(), f"<demo-cancel-{oid}@demo>", sender, f"Đơn hàng #{oid} đã bị hủy",
                               f"Mã đơn hàng: {oid} đã bị hủy theo yêu cầu."))
        emails.append((f"{month}-11", f"<demo-promo-{month}@demo>", "Shopee <info@mail.shopee.vn>",
                       f"Siêu sale {m}.{m} - Giảm đến 50%", "₫99.000 ₫199.000"))

        # MoMo bills as screenshots → OCR → parser
        for b_i, (service, provider, base, jit) in enumerate(BILLS):
            amount = jitter(base, jit) if jit else base
            if "điện EVN" in service:
                amount = int(round(amount * power, -3))
            day = [3, 12, 13, 15][b_i]
            img = DEMO / "momo" / f"momo-{month}-{b_i + 1}.png"
            momo_receipt(img, service.format(m=m), provider, amount,
                         f"{random.randint(7, 21):02d}:{random.randint(0, 59):02d} - {day:02d}/{m:02d}/{y}",
                         str(random.randint(10 ** 10, 10 ** 11 - 1)))
            cands = [c for c in parsers.parse_ocr_rows(ocr.ocr_rows(str(img))) if c["selected"]]
            stats["ocr_total"] += 1
            if cands and cands[0]["amount"] == amount:
                stats["ocr_ok"] += 1
            for c in cands:
                conn.execute("INSERT INTO transactions(date, amount, kind, description, source, category_id) "
                             "VALUES (?, ?, 'expense', ?, 'screenshot', ?)",
                             (c["date"], c["amount"], c["description"],
                              rules.categorize(conn, c["description"], "expense", compiled)))

    for received, mid, sender, subject, body in sorted(emails, key=lambda e: e[0]):  # stable: placed first
        status, tx_id = gmail_sync.process(conn, compiled, mid, received, sender, subject, body)
        conn.execute("INSERT INTO emails(message_id, received, sender, subject, body, status, transaction_id) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (mid, received, sender, subject, body, status, tx_id))
        stats["email"][status] = stats["email"].get(status, 0) + 1
    # Visa purchases typed in by hand (the bank sends no email), and October's card statement to reconcile.
    visa = "Visa Techcombank"
    meals = [("Phở Thìn Lò Đúc", 85_000), ("Highlands Coffee", 65_000), ("Gogi House Vincom", 1_200_000),
             ("Pizza 4P's Lê Thánh Tôn", 950_000), ("Uniqlo Vincom Đồng Khởi", 690_000), ("Bún chả Hương Liên", 120_000),
             ("The Coffee House", 59_000), ("Lotte Mart", 1_450_000)]
    typed = []
    for month in MONTHS:
        for name, price in random.sample(meals, 5):
            d = f"{month}-{random.randint(1, 24):02d}"
            amt = jitter(price, 0.1)
            conn.execute("INSERT INTO transactions(date, amount, description, source, category_id, pay_account) "
                         "VALUES (?, ?, ?, 'manual', ?, ?)", (d, amt, name, rules.categorize(conn, name, "expense", compiled), visa))
            typed.append((d, name, amt))
    if "2026-10" in MONTHS:
        from datetime import timedelta
        october = sorted(t for t in typed if t[0].startswith("2026-10"))
        stmt = []
        for i, (d, name, amt) in enumerate(october):
            if i == len(october) - 1:
                continue  # typed as Visa but actually paid in cash → "not on the statement"
            posted = (date.fromisoformat(d) + timedelta(days=random.choice([0, 1, 1, 2]))).isoformat()
            charged = amt + (round(amt * 0.1, -3) if i == 1 else 0)  # one dinner with a tip the receipt didn't show
            stmt.append((posted, name.upper(), charged, "expense"))
        stmt += [("2026-10-09", "GRAB*FOOD HCM", 168_000, "expense"), ("2026-10-21", "CGV CINEMAS VINCOM", 220_000, "expense"),
                 ("2026-10-15", "THANH TOAN THE - CAM ON", 8_000_000, "income")]
        for r in conn.execute("SELECT date, amount, description FROM transactions WHERE source = 'shopee' "
                              "AND status = 'ok' AND date LIKE '2026-10%' LIMIT 3"):
            stmt.append((r[0], "SHOPEE PAY " + r[2][:24].upper(), r[1], "expense"))
        stmt.sort()
        from samples import statement_pdf, statement_xlsx
        statement_xlsx(DEMO / "sao-ke-visa-thang-10.xlsx", stmt)
        statement_pdf(DEMO / "sao-ke-visa-thang-10.pdf", stmt, password="01011990")
        print(f"  Visa statement: {len(stmt)} lines → sao-ke-visa-thang-10.xlsx / .pdf (password 01011990)")

    db.set_setting(conn, "gmail_last_sync", "2026-10-31T09:30")
    conn.commit()

    print(f"Demo data in {DEMO}")
    print(f"  emails: {stats['email']}")
    print(f"  MoMo screenshots read correctly by OCR: {stats['ocr_ok']}/{stats['ocr_total']}")
    for r in conn.execute("SELECT source, COUNT(*), SUM(amount) FROM transactions GROUP BY source"):
        print(f"  {r[0]:<11} {r[1]:>3} giao dịch  {r[2]:>13,} ₫")


if __name__ == "__main__":
    main()
