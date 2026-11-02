"""Which Google Sheet (PRODUCTION / TEST) this Mac is connected to is always visible (docs/DEPLOY.md)."""
from playwright.sync_api import expect

import db


def connect_sheet(name, version=2):
    with db.connect() as c:
        for k, v in {"phone_connected": "1", "phone_sheet_url": "https://docs.google.com/spreadsheets/d/abc",
                     "phone_sheet_name": name, "phone_script_version": str(version)}.items():
            db.set_setting(c, k, v)


def test_test_sheet_shows_badge_and_name(onboarded, open_page):
    connect_sheet("Thu Chi — TEST")
    page = open_page()
    expect(page.locator("#envBadge")).to_be_visible()
    expect(page.locator("#envBadge")).to_have_text("TEST")
    page.click("nav [data-tab=import]")
    expect(page.locator("#phoneState")).to_contain_text("Thu Chi — TEST")
    page.click("nav [data-tab=settings]")
    expect(page.locator("#phoneSet")).to_contain_text("Thu Chi — TEST")


def test_production_sheet_has_no_badge(onboarded, open_page):
    connect_sheet("Thu Chi — PRODUCTION")
    page = open_page()
    expect(page.locator("#hello")).to_have_text("Chào Lan 👋")
    expect(page.locator("#envBadge")).to_be_hidden()
    page.click("nav [data-tab=import]")
    expect(page.locator("#phoneState")).to_contain_text("Thu Chi — PRODUCTION")
    expect(page.locator("#phoneState")).not_to_contain_text("bản cũ")


def test_old_code_gs_warns_with_the_fix(onboarded, open_page):
    connect_sheet("Thu Chi — PRODUCTION", version=1)
    page = open_page()
    page.click("nav [data-tab=import]")
    expect(page.locator("#phoneState")).to_contain_text("Code.gs trên Google là bản cũ")
    expect(page.locator("#phoneState")).to_contain_text("New version")
