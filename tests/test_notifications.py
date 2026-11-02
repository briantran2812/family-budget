"""The in-app bell."""
import notifications


def test_add_dedupe_read_and_trim(conn, monkeypatch):
    notifications.add(conn, "version", "✨", "Phiên bản 1.4.0", dedupe="version:1.4.0")
    notifications.add(conn, "version", "✨", "Phiên bản 1.4.0", dedupe="version:1.4.0")
    notifications.add(conn, "phone", "📱", "Đã lấy 2 khoản", link={"tab": "tx", "src": "phone"})
    got = notifications.listing(conn)
    assert got["unread"] == 2 and [i["title"] for i in got["items"]] == ["Đã lấy 2 khoản", "Phiên bản 1.4.0"]
    assert got["items"][0]["link"] == {"tab": "tx", "src": "phone"}
    notifications.mark_read(conn, got["items"][0]["id"])
    assert notifications.listing(conn)["unread"] == 1
    notifications.mark_read(conn)
    assert notifications.listing(conn)["unread"] == 0
    monkeypatch.setattr(notifications, "KEEP", 3)
    for i in range(5):
        notifications.add(conn, "phone", "📱", f"n{i}")
    assert [i["title"] for i in notifications.listing(conn)["items"]] == ["n4", "n3", "n2"]


def test_version_is_announced_once_to_existing_users_only(api):
    assert api.get("/api/notifications").get_json()["items"] == []     # new user: the welcome screen instead
    api.post("/api/profile", json={"onboarded": 1})
    api.get("/api/notifications")
    items = api.get("/api/notifications").get_json()["items"]
    assert len(items) == 1 and items[0]["link"] == {"whatsnew": True}
    assert api.post("/api/notifications/read", json={}).status_code == 200
    assert api.get("/api/notifications").get_json()["unread"] == 0


def test_phone_sync_and_push_error_notify(api, fake_sheet):
    api.post("/api/phone/connect", json={"code": fake_sheet["code"]})
    fake_sheet["rows"] = [{"id": "n1", "time": "2026-11-02T12:00:00", "amount": 45_000, "description": "Phở",
                           "account": "Tiền mặt", "by": "iPhone", "row": 2}]
    api.post("/api/phone/sync")
    api.post("/api/phone/sync")                                         # nothing new: no second entry
    import phone_inbox
    phone_inbox.keyring.set_password(phone_inbox.KEYRING_SERVICE, phone_inbox.KEYRING_USER, fake_sheet["code"] + "0")
    assert api.post("/api/phone/push").status_code == 400
    assert api.post("/api/phone/push").status_code == 400               # one error entry per day
    titles = [i["title"] for i in api.get("/api/notifications").get_json()["items"]]
    assert titles == ["Không ghi được bản sao lên Google Sheet", "Đã lấy 1 khoản mới từ iPhone"]
