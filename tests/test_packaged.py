"""Smoke test of the built .app — run by packaging/release.py with APP_PATH set; skipped otherwise."""
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request

import pytest

APP = os.environ.get("APP_PATH")
pytestmark = pytest.mark.skipif(not APP, reason="set APP_PATH to a built .app")


@pytest.fixture(scope="module")
def running_app():
    data = tempfile.mkdtemp(prefix="thuchi-packaged-")
    binary = os.path.join(APP, "Contents", "MacOS", os.path.basename(APP)[:-4])
    proc = subprocess.Popen([binary], env={**os.environ, "BUDGET_DATA": data},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    port = None
    for _ in range(60):
        out = subprocess.run(["lsof", "-nP", "-a", "-p", str(proc.pid), "-iTCP", "-sTCP:LISTEN"],
                             capture_output=True, text=True).stdout
        m = re.search(r":(\d+) \(LISTEN\)", out)
        if m:
            port = int(m.group(1))
            break
        time.sleep(0.5)
    assert port, "the app never started its local server"
    yield f"http://127.0.0.1:{port}", data
    proc.terminate()
    proc.wait(10)
    shutil.rmtree(data, ignore_errors=True)


def call(base, path, method="GET", body=None, files=None):
    import json
    headers = {"X-Budget": "1"}
    data = None
    if body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    if files:
        boundary = "----thuchi"
        name, content = files
        data = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{name}\"\r\n"
                f"Content-Type: image/png\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def test_window_loaded_ui_and_writes_log(running_app):
    base, data = running_app
    time.sleep(2)
    log = open(os.path.join(data, "app.log"), encoding="utf-8").read()
    assert '"GET / HTTP' in log and "GET /api/summary" in log  # the WebKit window fetched the page
    assert "Traceback" not in log


def test_info_reports_desktop_and_data_dir(running_app):
    base, data = running_app
    status, info = call(base, "/api/info")
    assert status == 200 and info["desktop"] is True and info["data_dir"] == data


def test_keychain_backend_available(running_app):
    assert call(running_app[0], "/api/gmail/accounts?address=nobody@example.com", "DELETE")[0] == 200


def test_ocr_inside_bundle(running_app, tmp_path):
    from samples import bank_receipt
    img = tmp_path / "b.png"
    bank_receipt(img, "Vietcombank", "NGUYEN VAN A", "Hoc phi thang 11", 6_500_000, "08:15 31/10/2026", "FT1")
    status, res = call(running_app[0], "/api/screenshot", "POST", files=("b.png", img.read_bytes()))
    assert status == 200 and res[0]["candidates"][0]["amount"] == 6_500_000


def test_gmail_tls_reaches_google(running_app):
    """A wrong password must be rejected *by Google* — proves the bundled CA certificates work."""
    status, res = call(running_app[0], "/api/gmail/accounts", "POST",
                       {"address": "qa.thuchi.check@gmail.com", "password": "abcdefghijklmnop"})
    if "kiểm tra mạng" in res.get("error", ""):
        pytest.skip("no network on this machine")
    assert status == 400 and "từ chối đăng nhập" in res["error"], res


def test_statement_import_inside_bundle(running_app, tmp_path):
    """openpyxl and PDFKit are imported lazily — make sure the bundle carries them."""
    from samples import statement_pdf, statement_xlsx
    rows = [("2026-10-03", "HIGHLANDS COFFEE", 65_000, "expense"), ("2026-10-15", "THANH TOAN THE", 5_000_000, "income")]
    for name, make in (("v.xlsx", statement_xlsx), ("v.pdf", statement_pdf)):
        f = tmp_path / name
        make(f, rows)
        boundary = "----thuchi"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"account\"\r\n\r\nVisa {name}\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
                f"Content-Type: application/octet-stream\r\n\r\n").encode() + f.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(running_app[0] + "/api/statements", data=body, method="POST",
                                     headers={"X-Budget": "1", "Content-Type": f"multipart/form-data; boundary={boundary}"})
        import json
        with urllib.request.urlopen(req, timeout=60) as r:
            rec = json.loads(r.read())
        assert rec["summary"]["lines"] == 2 and rec["summary"]["ignored_count"] == 1, (name, rec["summary"])
