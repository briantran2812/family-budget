"""UX test cases — IDs match docs/UX-TEST-CASES.md."""
import time

import pytest
from playwright.sync_api import expect

import db
import rules
from samples import momo_receipt, shopee_email
import parsers


def add_tx(date, amount, desc, kind="expense", source="manual", status="ok"):
    with db.connect() as c:
        c.execute("INSERT INTO transactions(date, amount, kind, description, source, category_id, status) "
                  "VALUES (?, ?, ?, ?, ?, ?, ?)", (date, amount, kind, desc, source,
                                                   rules.categorize(c, desc, kind), status))


def reload(page):
    page.wait_for_load_state("networkidle")  # reloading mid-request aborts it: "TypeError: Load failed" (flaky UX-01b)
    page.reload()
    page.wait_for_selector("#monthLabel:not(:empty)")


def toast(page):
    return page.locator(".toast").last


# ---------------------------------------------------------------- first run

def test_ux01_first_run_welcome_then_gmail_wizard(page):
    expect(page.get_by_text("Chào mừng đến với Thu Chi Gia Đình")).to_be_visible()
    page.fill("#wName", "Lan")
    page.get_by_role("button", name="Bắt đầu →").click()
    expect(page.locator("#hello")).to_have_text("Chào Lan 👋")
    expect(page.get_by_text("Bước 1 · Bật xác minh 2 bước")).to_be_visible()


def test_ux01b_welcome_skip_does_not_come_back(page):
    page.get_by_role("button", name="Bỏ qua").click()
    expect(page.locator(".modal")).to_have_count(0)
    reload(page)
    expect(page.locator(".modal")).to_have_count(0)


def test_ux02_wizard_steps_back_and_validation(onboarded, page, fake_gmail):
    page.locator("nav button[data-tab=settings]").click()
    page.locator("#settings").get_by_role("button", name="＋ Thêm Gmail").click()
    expect(page.get_by_text("Bước 1 · Bật xác minh 2 bước")).to_be_visible()
    expect(page.get_by_role("link", name="Mở trang Xác minh 2 bước ↗")).to_have_attribute(
        "href", "https://myaccount.google.com/signinoptions/twosv")
    page.get_by_role("button", name="Đã bật, tiếp →").click()
    expect(page.get_by_role("link", name="Mở trang Mật khẩu ứng dụng ↗")).to_have_attribute(
        "href", "https://myaccount.google.com/apppasswords")
    page.get_by_role("button", name="← Quay lại").click()
    expect(page.get_by_text("Bước 1 · Bật xác minh 2 bước")).to_be_visible()
    page.get_by_role("button", name="Đã bật, tiếp →").click()
    page.get_by_role("button", name="Đã sao chép, tiếp →").click()
    page.fill("#wAddr", "lan@gmail.com")
    page.fill("#wPass", "abc")
    page.get_by_role("button", name="Kết nối", exact=True).click()
    expect(page.locator("#wErr")).to_contain_text("16 ký tự")
    page.fill("#wPass", "wrong wrong wrong1")
    page.get_by_role("button", name="Kết nối", exact=True).click()
    expect(page.locator("#wErr")).to_contain_text("từ chối đăng nhập")


def test_ux03_wizard_connect_then_sync(onboarded, page, fake_gmail):
    oid = "261020ABCD1234"
    body = parsers.html_to_text(shopee_email(oid, [("Kem chống nắng Anessa 60ml", 1, 465_000)], 0, 0))
    fake_gmail["lan@gmail.com"] = [("2026-10-20T09:00:00", "<1>", "Shopee <info@mail.shopee.vn>",
                                    f"Xác nhận đơn hàng #{oid}", body)]
    page.locator("#addBtn").evaluate("() => gmailWizard(2)")
    page.fill("#wAddr", "lan@gmail.com")
    page.fill("#wPass", "abcd efgh ijkl mnop")
    page.get_by_role("button", name="Kết nối", exact=True).click()
    expect(page.get_by_text("Đã kết nối!")).to_be_visible()
    page.locator("#wSync").click()
    expect(page.locator("#syncResult")).to_contain_text("Đã nhập 1 đơn mới")
    expect(page.locator("#acctList")).to_contain_text("lan@gmail.com")
    page.locator("nav button[data-tab=overview]").click()
    expect(page.locator(".src-mini[data-src-link=shopee] .v")).to_have_text("465.000 ₫")


# ---------------------------------------------------------------- add / edit / delete

def test_ux04_add_expense_with_shorthand_amount(onboarded, page):
    page.locator("#addBtn").click()
    page.fill("#mAmt", "1,5tr")
    expect(page.locator("#mHint")).to_have_text("= 1.500.000 ₫")
    page.fill("#mDesc", "Học phí tháng 11 bé An")
    page.locator("#mSave").click()
    expect(toast(page)).to_have_text("Đã thêm 1.500.000 ₫")
    expect(page.locator("#hExpense")).to_have_text("1.500.000 ₫")
    expect(page.locator("#cats .cat").first).to_contain_text("Học phí")  # auto-categorised
    expect(page.locator("#recent .txrow").first).to_contain_text("Học phí tháng 11 bé An")


def test_ux05_invalid_amount_keeps_modal_open(onboarded, page):
    page.locator("#addBtn").click()
    page.fill("#mAmt", "abc")
    page.locator("#mSave").click()
    expect(toast(page)).to_have_text("Số tiền chưa hợp lệ")
    expect(page.locator(".modal")).to_be_visible()


def test_ux06_income_shows_share_spent(onboarded, page):
    add_tx(page.evaluate("todayISO()"), 10_000_000, "Học phí")
    page.locator("#addBtn").click()
    page.get_by_role("button", name="Khoản thu").click()
    page.fill("#mAmt", "50tr")
    page.fill("#mDesc", "Lương tháng 10")
    page.keyboard.press("Enter")  # Enter saves
    expect(page.locator("#hIncome")).to_have_text("50.000.000 ₫")
    expect(page.locator("#ring")).to_contain_text("20%")


def test_ux07_change_category_and_remember(onboarded, page):
    add_tx(page.evaluate("todayISO()"), 300_000, "Cần câu cá Shimano")
    add_tx(page.evaluate("todayISO()"), 200_000, "Mồi câu cá loại lớn")
    reload(page)
    page.locator("#recent .txrow", has_text="Cần câu cá").click()
    expect(page.get_by_text("Sửa giao dịch")).to_be_visible()
    page.locator(".catchip", has_text="Giải trí & du lịch").click()
    expect(page.locator("#mRemember")).to_be_visible()
    page.fill("#mKw", "câu cá")
    page.locator("#mSave").click()
    expect(toast(page)).to_contain_text("xếp lại 1 giao dịch")
    expect(page.locator("#cats .cat", has_text="Giải trí & du lịch")).to_contain_text("2 giao dịch")


def test_ux08_exclude_and_restore(onboarded, page):
    add_tx(page.evaluate("todayISO()"), 870_000, "Serum Vitamin C")
    reload(page)
    page.locator("#recent .txrow").first.click()
    page.get_by_role("button", name="Không tính").click()
    expect(page.locator("#hExpense")).to_have_text("0 ₫")
    expect(page.locator("#recent .txrow.cancelled")).to_have_count(1)
    page.locator("#recent .txrow").first.click()
    page.get_by_role("button", name="Tính lại").click()
    expect(page.locator("#hExpense")).to_have_text("870.000 ₫")


def test_ux09_delete_asks_first(onboarded, page):
    add_tx(page.evaluate("todayISO()"), 100_000, "Bánh mì")
    reload(page)
    page.locator("#recent .txrow").first.click()
    page.locator("#mDel").click()
    expect(page.get_by_text("Xoá giao dịch?")).to_be_visible()
    page.locator(".modal", has_text="Xoá giao dịch?").get_by_role("button", name="Huỷ").click()
    expect(page.locator("#recent .txrow")).to_have_count(1)
    page.keyboard.press("Escape")
    page.locator("#recent .txrow").first.click()
    page.locator("#mDel").click()
    page.locator("#okBtn").click()
    expect(toast(page)).to_have_text("Đã xoá")
    expect(page.locator("#recent .txrow")).to_have_count(0)


# ---------------------------------------------------------------- navigation & filters

def test_ux10_month_navigation(onboarded, page):
    add_tx("2026-09-15", 2_000_000, "Học phí tháng 9")
    reload(page)
    expect(page.locator("#todayBtn")).to_be_hidden()
    page.locator("#prevM").click()
    expect(page.locator("#monthLabel")).to_have_text("Tháng 9, 2026")
    expect(page.locator("#hExpense")).to_have_text("2.000.000 ₫")
    expect(page.locator("#todayBtn")).to_be_visible()
    page.locator("#todayBtn").click()
    expect(page.locator("#monthLabel")).to_have_text("Tháng 10, 2026")


def test_ux11_category_row_opens_filtered_list(onboarded, page):
    d = page.evaluate("todayISO()")
    add_tx(d, 6_500_000, "Học phí bé An")
    add_tx(d, 400_000, "Son kem lì Romand")
    reload(page)
    page.locator("#cats .cat", has_text="Mỹ phẩm").click()
    expect(page.locator("#tx")).to_be_visible()
    expect(page.locator("#txList .txrow")).to_have_count(1)
    expect(page.locator("#txList")).to_contain_text("Son kem lì")


def test_ux12_search_and_source_filter(onboarded, page):
    d = page.evaluate("todayISO()")
    add_tx(d, 465_000, "Kem chống nắng Anessa", source="shopee")
    add_tx(d, 189_000, "Son kem lì", source="tiktok")
    add_tx(d, 1_000_000, "Đi chợ")
    reload(page)
    page.locator("nav button[data-tab=tx]").click()
    expect(page.locator("#txList .txrow")).to_have_count(3)
    page.locator(".seg", has_text="TikTok").click()
    expect(page.locator("#txList .txrow")).to_have_count(1)
    page.locator(".seg", has_text="Tất cả").click()
    page.fill("#fText", "kem")
    expect(page.locator("#txList .txrow")).to_have_count(2)
    expect(page.locator("#txSum")).to_contain_text("2 giao dịch")


# ---------------------------------------------------------------- screenshots, budgets, sync

def test_ux13_screenshot_review_and_save(onboarded, page, tmp_path):
    img = tmp_path / "momo.png"
    momo_receipt(img, "Tiền điện EVN HCMC kỳ tháng 10", "EVN HCMC", 1_107_000, "09:10 - 12/10/2026", "123")
    page.locator("nav button[data-tab=import]").click()
    page.set_input_files("#files", str(img))
    row = page.locator("#ocrRows .ocr-row").first
    expect(row.locator(".amt")).to_have_value("1.107.000", timeout=15000)
    expect(row.locator(".desc")).to_have_value("Tiền điện EVN HCMC kỳ tháng 10")
    expect(row.locator(".cat option:checked")).to_contain_text("Điện nước")
    expect(page.locator("#ocrPay")).to_have_value("Ví MoMo")  # read off the receipt's "Nguồn tiền"
    row.locator(".amt").fill("1.110.000")  # the user corrects the amount before saving
    page.locator("#ocrSave").click()
    expect(toast(page)).to_have_text("Đã lưu 1 giao dịch")
    page.locator("nav button[data-tab=overview]").click()
    expect(page.locator("#cats .cat", has_text="Điện nước")).to_contain_text("1.110.000 ₫")
    expect(page.locator("#pays .cat", has_text="Ví MoMo")).to_contain_text("1.110.000 ₫")


def test_ux14_budget_warning(onboarded, page):
    add_tx(page.evaluate("todayISO()"), 1_200_000, "Son kem lì Romand")
    page.locator("nav button[data-tab=settings]").click()
    card = page.locator(".catcard", has_text="Mỹ phẩm & làm đẹp")
    card.locator(".bud").fill("1tr")
    card.locator(".bud").press("Tab")
    expect(toast(page)).to_have_text("Ngân sách 1 tr/tháng")
    page.locator("nav button[data-tab=overview]").click()
    expect(page.locator("#cats .cat", has_text="Mỹ phẩm")).to_contain_text("Vượt ngân sách 200k")


def test_ux15_empty_state_guides_new_user(onboarded, page):
    expect(page.get_by_text("Bắt đầu thôi!")).to_be_visible()
    for label in ("✉️ Kết nối Gmail", "📸 Thêm ảnh chụp", "✍️ Nhập tay"):
        expect(page.locator("#welcomeEmpty").get_by_role("button", name=label)).to_be_visible()
    expect(page.locator("#syncBtn")).to_be_hidden()  # nothing to sync before an account exists


def test_ux16_modal_closes_with_escape_and_backdrop(onboarded, page):
    page.locator("#addBtn").click()
    page.keyboard.press("Escape")
    expect(page.locator(".modal")).to_have_count(0)
    page.locator("#addBtn").click()
    page.mouse.click(10, 10)
    expect(page.locator(".modal")).to_have_count(0)


def test_ux17_phone_width_no_horizontal_scroll(onboarded, open_page):
    add_tx("2026-10-05", 6_500_000, "Học phí tháng 10 - Trường Mầm non Hoa Sen có tên rất dài")
    page = open_page(viewport={"width": 390, "height": 844})
    for tab in ("overview", "tx", "import", "settings"):
        page.locator(f"nav button[data-tab={tab}]").click()
        assert page.evaluate("document.documentElement.scrollWidth") <= 390, tab
    box = page.locator(".side").bounding_box()
    assert box["y"] > 700  # navigation moved to the bottom


def test_ux18_dark_mode_follows_system(onboarded, open_page):
    page = open_page(color_scheme="dark")
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(15, 16, 23)"


def test_ux21_unparsed_email_can_be_dismissed(onboarded, page):
    with db.connect() as c:
        c.execute("INSERT INTO emails(message_id, received, sender, subject, body, status) VALUES "
                  "('<x>', '2026-10-20', 'Shopee', 'Đơn hàng #261020X đã giao thành công', 'Cảm ơn', 'no_amount')")
    page.locator("nav button[data-tab=import]").click()
    expect(page.locator("#emails details")).to_have_count(1)
    page.locator("#emails .dismiss").click()
    expect(page.locator("#emails")).to_contain_text("Không có email nào")


def test_ux22_csv_export(onboarded, page):
    add_tx("2026-10-05", 100_000, "Học phí bé An")
    r = page.request.get(page.url.split("#")[0] + "api/export.csv")
    assert r.headers["content-disposition"].startswith("attachment; filename=thu-chi-")
    assert r.text().startswith("﻿Ngày,") and "Học phí bé An" in r.text()


def test_ux23_remove_gmail_account_asks_first(onboarded, page, fake_gmail):
    import gmail_sync
    with db.connect() as c:
        gmail_sync.add_account(c, "lan@gmail.com", "abcdefghijklmnop")
    reload(page)
    page.locator("nav button[data-tab=settings]").click()
    page.locator("#acctSettings").get_by_role("button", name="Gỡ").click()
    page.locator("#okBtn").click()
    expect(page.locator("#acctSettings")).to_contain_text("Chưa có tài khoản nào")


def test_ux24_every_tab_renders_without_errors(onboarded, page):
    add_tx("2026-10-05", 100_000, "Học phí")
    for tab in ("overview", "tx", "import", "settings", "overview"):
        page.locator(f"nav button[data-tab={tab}]").click()
        expect(page.locator(f"#{tab}")).to_be_visible()
    # the page fixture fails the test on any JavaScript error


def test_ux25_one_year_of_data_loads_fast(onboarded, page):
    import random
    random.seed(1)
    with db.connect() as c:
        cats = [r[0] for r in c.execute("SELECT id FROM categories WHERE kind='expense'")]
        c.executemany("INSERT INTO transactions(date, amount, description, source, category_id) VALUES (?,?,?,?,?)",
                      [(f"2026-{random.randint(1, 10):02d}-{random.randint(1, 28):02d}", random.randint(20, 3000) * 1000,
                        f"Giao dịch {i}", random.choice(["shopee", "tiktok", "manual"]), random.choice(cats))
                       for i in range(3000)])
    start = time.perf_counter()
    reload(page)
    page.locator("nav button[data-tab=tx]").click()
    expect(page.locator("#txList .txrow").first).to_be_visible()
    assert time.perf_counter() - start < 3, "overview + month list should load within 3 s with 3,000 rows"


# ---------------------------------------------------------------- 1.3.0: statements & reconciliation

STMT_ROWS = [
    ("2026-10-03", "HIGHLANDS COFFEE Q1", 65_000, "expense"),
    ("2026-10-12", "GOGI HOUSE VINCOM", 1_350_000, "expense"),
    ("2026-10-18", "CIRCLE K NGUYEN HUE", 89_000, "expense"),
    ("2026-10-15", "THANH TOAN THE - CAM ON", 5_000_000, "income"),
]


def visa_entries():
    with db.connect() as c:
        for d, amt, desc in [("2026-10-02", 65_000, "Cà phê Highlands"), ("2026-10-12", 1_200_000, "Ăn tối Gogi"),
                             ("2026-10-16", 250_000, "Nhà sách Fahasa")]:
            c.execute("INSERT INTO transactions(date, amount, description, source, category_id, pay_account) "
                      "VALUES (?, ?, ?, 'manual', ?, 'Visa Techcombank')", (d, amt, desc, rules.categorize(c, desc)))


def import_statement(page, tmp_path, name="saoke.csv", data=None):
    from samples import statement_csv
    f = tmp_path / name
    f.write_bytes(data if data is not None else statement_csv(STMT_ROWS))
    page.locator("nav button[data-tab=recon]").click()
    page.fill("#stmtForm [name=account]", "Visa Techcombank")
    page.set_input_files("#stmtInput", str(f))
    expect(page.locator("#stmtFile")).to_have_text(name)
    page.locator("#stmtGo").click()


def test_ux26_import_statement_shows_buckets(onboarded, page, tmp_path):
    visa_entries()
    import_statement(page, tmp_path)
    expect(toast(page)).to_have_text("Đã nhập 4 dòng sao kê")
    tiles = page.locator(".rec-tile")
    expect(tiles.nth(0)).to_contain_text("1")              # coffee matched despite the 1-day posting lag
    expect(tiles.nth(1)).to_contain_text("1.439.000 ₫")    # Gogi (near) + Circle K
    expect(tiles.nth(1)).to_contain_text("1 gần khớp")
    expect(tiles.nth(2)).to_contain_text("250.000 ₫")      # Fahasa: typed as Visa, not on the statement
    expect(tiles.nth(3)).to_contain_text("1")              # the card payment, auto-ignored
    expect(page.locator(".sugg")).to_contain_text("Ăn tối Gogi")


def test_ux27_add_forgotten_card_charge(onboarded, page, tmp_path):
    visa_entries()
    import_statement(page, tmp_path)
    row = page.locator(".recrow", has_text="CIRCLE K")
    row.get_by_role("button", name="＋ Thêm vào app").click()
    expect(toast(page)).to_have_text("Đã thêm vào app")
    expect(page.locator(".rec-tile").nth(1)).to_contain_text("1.350.000 ₫")
    page.locator("nav button[data-tab=tx]").click()
    expect(page.locator("#txList .txrow", has_text="CIRCLE K")).to_contain_text("Sao kê")
    expect(page.locator("#txList .txrow", has_text="CIRCLE K")).to_contain_text("💳 Visa Techcombank")


def test_ux28_near_match_fix_amount(onboarded, page, tmp_path):
    visa_entries()
    import_statement(page, tmp_path)
    page.locator(".recrow", has_text="GOGI").get_by_role("button", name="Ghép, sửa thành số sao kê").click()
    expect(toast(page)).to_have_text("Đã ghép và sửa số tiền")
    expect(page.locator(".rec-tile").nth(0)).to_contain_text("2")
    page.locator("nav button[data-tab=tx]").click()
    expect(page.locator("#txList .txrow", has_text="Ăn tối Gogi")).to_contain_text("1.350.000 ₫")


def test_ux29_password_pdf(onboarded, page, tmp_path):
    from samples import statement_pdf
    pdf = tmp_path / "visa.pdf"
    statement_pdf(pdf, STMT_ROWS, password="01011990")
    import_statement(page, tmp_path, "visa.pdf", pdf.read_bytes())
    expect(page.locator("#stmtMsg")).to_contain_text("mật khẩu")
    expect(page.locator("#stmtPass")).to_be_visible()
    page.fill("#stmtPass", "sai")
    page.locator("#stmtGo").click()
    expect(page.locator("#stmtMsg")).to_contain_text("Sai mật khẩu")
    page.fill("#stmtPass", "01011990")
    page.locator("#stmtGo").click()
    expect(toast(page)).to_have_text("Đã nhập 4 dòng sao kê")
    expect(page.locator("#stmtPass")).to_be_hidden()


def test_ux30_manual_link_picker_and_ignore(onboarded, page, tmp_path):
    visa_entries()
    import_statement(page, tmp_path)
    page.locator(".recrow", has_text="CIRCLE K").get_by_role("button", name="Ghép với…").click()
    expect(page.locator("#pickList .txrow").first).to_be_visible()
    page.locator("#pickList .txrow", has_text="Nhà sách Fahasa").click()
    expect(toast(page)).to_have_text("Đã ghép")
    expect(page.locator(".modal")).to_have_count(0)  # picking does not open the edit dialog
    page.locator(".recrow", has_text="GOGI").get_by_role("button", name="Bỏ qua").click()
    expect(page.locator(".rec-tile").nth(1)).to_contain_text("0")
    expect(page.get_by_text("Mọi dòng trên sao kê đều đã có trong app")).to_be_visible()


def test_ux31_pay_account_remembered(onboarded, page):
    page.locator("#addBtn").click()
    page.fill("#mAmt", "120k")
    page.fill("#mDesc", "Bún bò")
    page.fill("#mPay", "Visa Techcombank")
    page.locator("#mSave").click()
    expect(page.locator("#recent .txrow").first).to_contain_text("💳 Visa Techcombank")
    page.locator("#addBtn").click()
    expect(page.locator("#mPay")).to_have_value("Visa Techcombank")  # next entry defaults to the same card


def test_ux32_mini_cards_open_filtered_list(onboarded, page):
    d = page.evaluate("todayISO()")
    add_tx(d, 465_000, "Kem chống nắng", source="shopee")
    add_tx(d, 189_000, "Son kem", source="tiktok")
    add_tx(d, 50_000, "Bánh mì")
    reload(page)
    page.locator("[data-src-link=shopee]").click()
    expect(page.locator("#tx")).to_be_visible()
    expect(page.locator("#txList .txrow")).to_have_count(1)
    expect(page.locator("#fSrc .seg.on")).to_have_text("Shopee")
    page.locator("nav button[data-tab=overview]").click()
    page.locator("[data-src-link=tiktok]").click()
    expect(page.locator("#txList")).to_contain_text("Son kem")
    page.locator("nav button[data-tab=overview]").click()
    page.locator("[data-src-link='']").click()
    expect(page.locator("#txList .txrow")).to_have_count(3)


def test_ux33_card_entry_missing_from_statement_opens_editor(onboarded, page, tmp_path):
    visa_entries()
    import_statement(page, tmp_path)
    page.locator("#recResult .txrow", has_text="Nhà sách Fahasa").click()
    expect(page.get_by_text("Sửa giao dịch")).to_be_visible()  # even though it is not the month on screen
    expect(page.locator("#mPay")).to_have_value("Visa Techcombank")


# ---------------------------------------------------------------- iPhone via Google Sheet

def phone_row(rid, amount, desc, time="2026-10-30T12:30:00", account="Tiền mặt"):
    return {"id": rid, "time": time, "amount": amount, "description": desc, "account": account, "by": "iPhone", "row": 2}


def test_ux34_connect_iphone_then_entries_appear(onboarded, page, fake_sheet):
    PHONE_CODE = fake_sheet["code"]
    fake_sheet["rows"] = [phone_row("p1", 45_000, "Phở bò"), phone_row("p2", 1_500_000, "Học phí tháng 10")]
    page.locator("nav button[data-tab=import]").click()
    page.locator("#phoneConnectBtn").click()
    page.fill("#pwCode", "sai mã")
    page.locator("#pwGo").click()
    expect(page.locator("#pwMsg")).to_contain_text("Mã kết nối có dạng")
    page.fill("#pwCode", PHONE_CODE)
    page.locator("#pwGo").click()
    expect(toast(page)).to_contain_text("Đã lấy 2 khoản mới từ iPhone")
    expect(page.locator("#phoneSyncBtn")).to_be_visible()
    expect(page.locator("#phoneConnectBtn")).to_be_hidden()
    page.locator("nav button[data-tab=tx]").click()
    page.locator("#fSrc .seg[data-src=phone]").click()
    expect(page.locator("#txList .txrow")).to_have_count(2)
    expect(page.locator("#txList")).to_contain_text("Học phí")


def test_ux35_opening_the_app_pulls_new_phone_entries(onboarded, open_page, fake_sheet):
    PHONE_CODE = fake_sheet["code"]
    import phone_inbox
    with db.connect() as c:
        phone_inbox.connect(c, PHONE_CODE)
    fake_sheet["rows"] = [phone_row("q1", 30_000, "Gửi xe")]
    p = open_page()
    expect(p.locator(".toast").last).to_contain_text("Đã lấy 1 khoản từ iPhone")
    expect(p.locator("#recent")).to_contain_text("Gửi xe")
    p.locator("nav button[data-tab=import]").click()
    p.locator("#phoneSyncBtn").click()  # nothing new: says so instead of a silent no-op
    expect(p.locator("#phoneResult")).to_contain_text("Đã lấy 0 khoản mới")
    expect(p.locator("#phoneResult")).to_contain_text("1 đã có")


def test_ux36_iphone_settings_copy_code_and_disconnect(onboarded, page, fake_sheet):
    PHONE_CODE = fake_sheet["code"]
    import phone_inbox
    with db.connect() as c:
        phone_inbox.connect(c, PHONE_CODE)
    reload(page)
    page.locator("nav button[data-tab=settings]").click()
    expect(page.locator("#phoneSet")).to_contain_text("Đã kết nối")
    page.locator("#phoneCopy").click()
    expect(toast(page)).to_contain_text("Đã sao chép mã")
    page.locator("#phoneOff").click()
    page.locator("#okBtn").click()
    expect(page.locator("#phoneSet")).to_contain_text("Kết nối Google Sheet")


def test_ux37_pay_method_icon_and_filter(onboarded, page):
    d = page.evaluate("todayISO()")
    with db.connect() as c:
        for amount, desc, pay in [(45_000, "Ăn uống", "Tiền mặt"), (250_000, "Cà phê", "Visa Techcombank"),
                                  (120_000, "Tiền điện", "Chuyển khoản"), (60_000, "Trà sữa", "Ví MoMo"),
                                  (30_000, "Gửi xe", None)]:
            c.execute("INSERT INTO transactions(date, amount, description, pay_account) VALUES (?, ?, ?, ?)",
                      (d, amount, desc, pay))
    reload(page)
    page.locator("nav button[data-tab=tx]").click()
    row = lambda text: page.locator("#txList .txrow", has_text=text)
    expect(row("Ăn uống")).to_contain_text("💵 Tiền mặt")
    expect(row("Cà phê")).to_contain_text("💳 Visa Techcombank")
    expect(row("Tiền điện")).to_contain_text("🏦 Chuyển khoản")
    expect(row("Trà sữa")).to_contain_text("👛 Ví MoMo")
    page.select_option("#fPay", "Tiền mặt")
    expect(page.locator("#txList .txrow")).to_have_count(1)
    expect(page.locator("#txSum")).to_contain_text("chi 45.000")
    page.select_option("#fPay", "-")
    expect(page.locator("#txList .txrow")).to_have_count(1)
    expect(page.locator("#txList")).to_contain_text("Gửi xe")
    page.select_option("#fPay", "")
    expect(page.locator("#txList .txrow")).to_have_count(5)


def test_ux38_overview_by_pay_method_and_top_sources(onboarded, page):
    d = page.evaluate("todayISO()")
    with db.connect() as c:
        for amount, desc, pay, src in [(45_000, "Ăn uống", "Tiền mặt", "phone"), (30_000, "Gửi xe", "Tiền mặt", "phone"),
                                       (250_000, "Cà phê", "Visa Techcombank", "manual"), (60_000, "Son", None, "shopee")]:
            c.execute("INSERT INTO transactions(date, amount, description, pay_account, source) VALUES (?, ?, ?, ?, ?)",
                      (d, amount, desc, pay, src))
    reload(page)
    pays = page.locator("#pays .cat")
    expect(pays).to_have_count(3)
    expect(pays.nth(0)).to_contain_text("💳")
    expect(page.locator("#pays")).to_contain_text("💵")
    expect(page.locator("#pays")).to_contain_text("Chưa ghi cách trả")
    cash = page.locator("#pays .cat", has_text="Tiền mặt")
    expect(cash).to_contain_text("75.000")
    minis = page.locator(".src-mini")
    expect(minis.nth(0)).to_contain_text("Nhập tay")   # biggest source first, not always Shopee/TikTok
    expect(minis.nth(1)).to_contain_text("iPhone")
    cash.click()
    expect(page.locator("#tx")).to_be_visible()
    expect(page.locator("#fPay")).to_have_value("Tiền mặt")
    expect(page.locator("#txList .txrow")).to_have_count(2)



def test_ux39_mirror_to_sheet_settings(onboarded, page, fake_sheet):
    import phone_inbox
    with db.connect() as c:
        phone_inbox.connect(c, fake_sheet["code"])
        db.set_setting(c, "device_name", "MacBook Lan")
    add_tx(page.evaluate("todayISO()"), 45_000, "Phở")
    reload(page)
    page.locator("nav button[data-tab=settings]").click()
    expect(page.locator("#devName")).to_have_value("MacBook Lan")
    expect(page.locator("#pushStatus")).to_contain_text("Chưa đẩy lần nào")
    page.locator("#pushNow").click()
    expect(toast(page)).to_contain_text("Đã đẩy 1 giao dịch")
    expect(page.locator("#pushStatus")).to_contain_text("Đã đẩy lên lúc")
    assert fake_sheet["pushes"][-1]["device"] == "MacBook Lan"
    page.locator("#pushOn").uncheck()
    expect(page.locator("#pushNow")).to_be_disabled()



def test_ux40_header_sync_button(onboarded, page, fake_sheet, fake_gmail):
    expect(page.locator("#syncAllBtn")).to_be_hidden()      # nothing connected: nothing to sync
    import phone_inbox
    with db.connect() as c:
        phone_inbox.connect(c, fake_sheet["code"])
    reload(page)
    expect(page.locator("#syncAllBtn")).to_be_visible()
    page.locator("#syncAllBtn").click()
    expect(toast(page)).to_contain_text("không có gì mới")
    fake_sheet["rows"] = [phone_row("h1", 35_000, "Bánh mì")]
    page.locator("#syncAllBtn").click()
    expect(toast(page)).to_contain_text("Đã lấy 1 khoản từ iPhone")
    expect(page.locator("#recent")).to_contain_text("Bánh mì")



def test_ux41_small_share_of_income_is_not_shown_as_zero(onboarded, page):
    d = page.evaluate("todayISO()")
    add_tx(d, 50_000_000, "Lương", kind="income")
    add_tx(d, 237_590, "Đổ xăng")
    reload(page)
    expect(page.locator("#ring")).to_contain_text("0,5%")



def test_ux42_whats_new_once_per_version_and_on_demand(page):
    with db.connect() as c:
        db.set_setting(c, "onboarded", "1")
        db.set_setting(c, "seen_version", "1.3.0")   # someone updating from an older version
    reload(page)
    expect(page.get_by_text("Có gì mới trong 1.4.0")).to_be_visible()
    expect(page.locator("#wnCur .wn-item")).to_have_count(7)
    page.get_by_role("button", name="Đã hiểu").click()
    reload(page)
    page.wait_for_timeout(300)
    expect(page.locator(".modal")).to_have_count(0)       # shown once per version
    page.locator("#wnLink").click()                       # …and on demand from the sidebar
    page.locator(".wn-item", has_text="Đối chiếu sao kê").get_by_role("button", name="Xem →").click()
    expect(page.locator("#recon")).to_be_visible()
    page.locator("nav button[data-tab=settings]").click()
    page.locator("#aboutWn").click()
    expect(page.get_by_text("Có gì mới trong 1.4.0")).to_be_visible()


def test_ux42b_new_user_gets_welcome_not_whats_new(page):
    expect(page.get_by_text("Chào mừng đến với Thu Chi Gia Đình")).to_be_visible()
    page.get_by_role("button", name="Bỏ qua").click()
    reload(page)
    page.wait_for_timeout(300)
    expect(page.locator(".modal")).to_have_count(0)


def test_ux43_budget_alert_banner_pill_and_click_through(onboarded, page):
    d = page.evaluate("todayISO()")
    with db.connect() as c:
        c.execute("UPDATE categories SET budget = 2000000 WHERE name = 'Ăn uống & đi chợ'")
    add_tx(d, 1_580_000, "Đi chợ Bách Hoá Xanh")  # 79%: no alert yet
    reload(page)
    expect(page.locator("#cats .cat", has_text="Ăn uống")).to_contain_text("Ngân sách 2 tr · còn 420k")
    expect(page.locator("#budgetAlerts")).to_be_hidden()
    add_tx(d, 120_000, "Trà sữa")
    with db.connect() as c:
        c.execute("UPDATE categories SET budget = 1000000 WHERE name = 'Mỹ phẩm & làm đẹp'")
    add_tx(d, 1_250_000, "Son kem lì Romand")
    reload(page)
    rows = page.locator("#budgetAlerts .alert")
    expect(rows).to_have_count(2)
    expect(rows.first).to_have_class("alert over")  # the worst one first
    expect(rows.first).to_contain_text("Mỹ phẩm & làm đẹp đã vượt ngân sách tháng 250k (1,3 tr / 1 tr)")
    expect(rows.nth(1)).to_contain_text("Ăn uống & đi chợ đã dùng 85% ngân sách tháng (1,7 tr / 2 tr) — còn 300k")
    expect(page.locator("#cats .cat", has_text="Ăn uống").locator(".pill.warn")).to_have_text(
        "Đã dùng 85% ngân sách · còn 300k")
    expect(page.locator("#cats .cat", has_text="Mỹ phẩm").locator(".pill.bad")).to_have_text("⚠ Vượt ngân sách 250k")
    rows.nth(1).click()
    expect(page.locator("#tx")).to_be_visible()
    expect(page.locator("#txList .txrow")).to_have_count(2)
    expect(page.locator("#txList")).to_contain_text("Trà sữa")


def test_ux43b_budget_alerts_fit_a_phone(onboarded, open_page):
    with db.connect() as c:
        c.execute("UPDATE categories SET budget = 1000000 WHERE name IN ('Ăn uống & đi chợ', 'Mỹ phẩm & làm đẹp')")
    add_tx("2026-10-05", 850_000, "Đi chợ Bách Hoá Xanh")
    add_tx("2026-10-05", 1_250_000, "Son kem lì Romand")
    page = open_page(viewport={"width": 390, "height": 844})
    expect(page.locator("#budgetAlerts .alert")).to_have_count(2)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
