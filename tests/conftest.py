"""Every test gets its own empty database; nothing touches ~/Library or the network."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["BUDGET_DATA"] = tempfile.mkdtemp(prefix="thuchi-test-")  # before db is imported anywhere

import pytest  # noqa: E402

import db  # noqa: E402


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
