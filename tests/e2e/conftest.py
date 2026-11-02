"""End-to-end UX tests: the real page in WebKit (the engine of the app's window) against a live server."""
import threading
from datetime import datetime

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

import db
import gmail_sync
from app import VERSION, app


@pytest.fixture(scope="session")
def server():
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.webkit.launch()
        yield b
        b.close()


@pytest.fixture
def onboarded(fresh_db):
    with db.connect() as c:
        db.set_setting(c, "onboarded", "1")
        db.set_setting(c, "seen_version", VERSION)  # "Có gì mới" has its own test (UX-42)
        db.set_setting(c, "user_name", "Lan")


@pytest.fixture
def fake_gmail(monkeypatch, fake_keyring):
    """Gmail that accepts any 16-char password and serves `mailbox[address]`."""
    mailbox = {}

    class FakeImap:
        def logout(self):
            pass

    def fake_login(address, password):
        if password == "wrongwrongwrong1":
            raise gmail_sync.SyncError(f"Gmail từ chối đăng nhập {address}. Kiểm tra lại App Password "
                                       "(16 ký tự, không phải mật khẩu Gmail thường).")
        return FakeImap()

    monkeypatch.setattr(gmail_sync, "_login", fake_login)
    monkeypatch.setattr(gmail_sync, "_fetch_new", lambda c, a, q: (len(mailbox.get(a, [])), mailbox.get(a, [])))
    return mailbox


FROZEN_NOW = datetime(2026, 10, 31, 10, 0)


def _page(browser, server, **ctx):
    context = browser.new_context(viewport=ctx.pop("viewport", {"width": 1280, "height": 860}), locale="vi-VN", **ctx)
    page = context.new_page()
    page.clock.set_fixed_time(FROZEN_NOW)  # the fixtures are dated October 2026; "this month" must not drift
    page.js_errors = []
    page.on("pageerror", lambda e: page.js_errors.append(str(e)))
    page.goto(server + "/")
    page.wait_for_selector("#monthLabel:not(:empty)")
    return page


@pytest.fixture
def page(browser, server, fresh_db):
    p = _page(browser, server)
    yield p
    assert p.js_errors == [], p.js_errors  # every UX test also fails on a JavaScript error
    p.context.close()


@pytest.fixture
def open_page(browser, server, fresh_db):
    """Factory for tests that need a special viewport or colour scheme."""
    pages = []

    def make(**ctx):
        pages.append(_page(browser, server, **ctx))
        return pages[-1]
    yield make
    for p in pages:
        assert p.js_errors == [], p.js_errors
        p.context.close()
