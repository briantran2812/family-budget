"""Real macOS Vision OCR on rendered MoMo receipts."""
import random
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS Vision only")


@pytest.mark.parametrize("service,amount", [
    ("Học phí tháng 10 - bé An", 6_500_000), ("Tiền điện EVN HCMC kỳ tháng 10", 1_107_000),
    ("Tiền nước Sawaco kỳ tháng 10", 366_000), ("Cước internet FPT tháng 10", 280_000),
    ("Nạp tiền điện thoại Viettel", 100_000), ("Thanh toán Bách Hoá Xanh", 1_234_567),
])
def test_momo_receipt(tmp_path, service, amount):
    import ocr
    import parsers
    from samples import momo_receipt
    img = tmp_path / "r.png"
    momo_receipt(img, service, "Nhà cung cấp", amount, "14:32 - 10/10/2026", str(random.randint(10**10, 10**11)))
    [c] = [c for c in parsers.parse_ocr_rows(ocr.ocr_rows(str(img))) if c["selected"]]
    assert (c["amount"], c["description"], c["date"]) == (amount, service, "2026-10-10")


def test_api_screenshot_endpoint(api, tmp_path):
    from samples import momo_receipt
    img = tmp_path / "r.png"
    momo_receipt(img, "Học phí tháng 10 - bé An", "Trường", 6_500_000, "08:00 - 03/10/2026", "1")
    with open(img, "rb") as f:
        r = api.post("/api/screenshot", data={"files": (f, "r.png")})
    [c] = r.json[0]["candidates"]
    cats = {c["id"]: c["name"] for c in api.get("/api/categories").json}
    assert c["amount"] == 6_500_000 and cats[c["category_id"]] == "Học phí"


@pytest.mark.parametrize("bank,content,amount,want_cat", [
    ("Vietcombank", "Hoc phi thang 11 be An", 6_500_000, "Học phí"),
    ("Techcombank", "Thanh toan tien dien thang 10", 1_250_000, "Điện nước"),
    ("MB Bank", "Chuyen tien cho me", 3_000_000, "Khác"),
])
def test_bank_transfer_receipt(api, tmp_path, bank, content, amount, want_cat):
    """Bank-app transfer screenshots go through the same OCR path as MoMo."""
    from samples import bank_receipt
    img = tmp_path / "b.png"
    bank_receipt(img, bank, "NGUYEN VAN A", content, amount, "08:15 31/10/2026", "FT26304123456")
    with open(img, "rb") as f:
        [res] = api.post("/api/screenshot", data={"files": (f, "b.png")}).json
    [c] = [c for c in res["candidates"] if c["selected"]]
    cats = {c["id"]: c["name"] for c in api.get("/api/categories").json}
    assert (c["amount"], c["description"], c["date"], cats[c["category_id"]]) == \
        (amount, content, "2026-10-31", want_cat)


@pytest.mark.parametrize("ver", ["11.7.10", "12.7.6", "10.16"])
def test_older_macos_gets_a_friendly_message_not_a_crash(api, tmp_path, monkeypatch, ver):
    """The app runs from macOS 11, but Vision reads Vietnamese only from macOS 13."""
    import platform
    monkeypatch.setattr(platform, "mac_ver", lambda: (ver, ("", "", ""), "x86_64"))
    img = tmp_path / "r.png"
    img.write_bytes(b"not read")
    with open(img, "rb") as f:
        r = api.post("/api/screenshot", data={"files": (f, "r.png")})
    assert r.status_code == 200
    [res] = r.json
    assert res["candidates"] == [] and res["error"].startswith("Đọc ảnh cần macOS 13 trở lên")
    assert f"macOS {'.'.join(ver.split('.')[:2])}" in res["error"]


def test_macos_13_and_later_are_supported(monkeypatch):
    import platform
    import ocr
    for ver in ("13.0", "14.6.1", "26.5.2"):
        monkeypatch.setattr(platform, "mac_ver", lambda v=ver: (v, ("", "", ""), "arm64"))
        assert ocr.unsupported_reason() is None, ver
