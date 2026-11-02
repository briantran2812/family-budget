"""Every test gets its own empty database; nothing touches ~/Library or the network."""
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["BUDGET_DATA"] = tempfile.mkdtemp(prefix="thuchi-test-")  # before db is imported anywhere

import pytest  # noqa: E402

import db  # noqa: E402


@pytest.fixture(autouse=True)
def piggy_today(monkeypatch):
    """The server's "today" for the piggy bank: the last day of October 2026, the same day the E2E browser clock shows."""
    import piggy
    monkeypatch.setattr(piggy, "today", lambda: date(2026, 10, 31))


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "budget.db")
    db.init()
    return tmp_path


@pytest.fixture
def conn(fresh_db):
    c = db.connect()
    yield c
    c.close()


@pytest.fixture
def client(fresh_db):
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


class Api:
    """Test client that sends what the real page sends (host + X-Budget header)."""
    BASE = "http://127.0.0.1:8765"

    def __init__(self, client):
        self.c = client

    def get(self, path, **kw):
        return self.c.get(path, base_url=self.BASE, **kw)

    def _send(self, method, path, **kw):
        return getattr(self.c, method)(path, base_url=self.BASE, headers={"X-Budget": "1"}, **kw)

    def post(self, path, **kw):
        return self._send("post", path, **kw)

    def patch(self, path, **kw):
        return self._send("patch", path, **kw)

    def delete(self, path, **kw):
        return self._send("delete", path, **kw)


@pytest.fixture
def api(client):
    return Api(client)


@pytest.fixture
def fake_keyring(monkeypatch):
    """In-memory Keychain so tests never write the real one."""
    import gmail_sync
    store = {}
    monkeypatch.setattr(gmail_sync.keyring, "set_password", lambda s, u, p: store.__setitem__((s, u), p))
    monkeypatch.setattr(gmail_sync.keyring, "get_password", lambda s, u: store.get((s, u)))
    monkeypatch.setattr(gmail_sync.keyring, "delete_password", lambda s, u: store.pop((s, u), None))
    return store


PHONE_CODE = "https://script.google.com/macros/s/AKfyc-test_1/exec?k=0123456789abcdef01234567"


@pytest.fixture
def fake_sheet(monkeypatch, fake_keyring):
    """Fake web app: `rows` is what action=list returns."""
    import phone_inbox
    state = {"rows": [], "calls": [], "code": PHONE_CODE, "name": "Thu Chi — PRODUCTION",
             "version": phone_inbox.REQUIRED_SCRIPT_VERSION}
    monkeypatch.setattr(phone_inbox.keyring, "set_password", lambda s, u, p: fake_keyring.__setitem__((s, u), p))
    monkeypatch.setattr(phone_inbox.keyring, "get_password", lambda s, u: fake_keyring.get((s, u)))
    monkeypatch.setattr(phone_inbox.keyring, "delete_password", lambda s, u: fake_keyring.pop((s, u), None))

    def fake_get(code, action):
        state["calls"].append((code, action))
        if code != PHONE_CODE:
            raise phone_inbox.InboxError("Apps Script báo lỗi: Mã kết nối sai. Lấy lại mã kết nối bằng layMaKetNoi.")
        script = {"name": state["name"], "version": state["version"]}  # what Code.gs SCRIPT_VERSION 2+ adds
        if action == "ping":
            return {"ok": True, "sheet": "https://docs.google.com/spreadsheets/d/abc", **script}
        return {"ok": True, "rows": state["rows"], **script}
    monkeypatch.setattr(phone_inbox, "_get", fake_get)
    state["pushes"] = []

    def fake_post(code, payload):
        if code != PHONE_CODE:
            raise phone_inbox.InboxError("Apps Script báo lỗi: Mã kết nối sai.")
        state["pushes"].append(payload)
        return {"ok": True, "rows": len(payload["rows"]), "summary": len(payload["summary"])}
    monkeypatch.setattr(phone_inbox, "_post", fake_post)
    import app as app_module  # a real timer would fire after the test, against the real network
    state["scheduled"] = []
    monkeypatch.setattr(app_module, "schedule_push", lambda delay=None: state["scheduled"].append(delay))
    return state
