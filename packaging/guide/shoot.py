"""Screenshots for the user guide, taken from the real app in WebKit (light mode, retina)."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "img"
PY = ROOT / ".venv" / "bin" / "python"
sys.path.insert(0, str(ROOT))


def serve(data_dir: Path, port: int) -> subprocess.Popen:
    p = subprocess.Popen([str(PY), "app.py", "--port", str(port)], cwd=ROOT, env={**os.environ, "BUDGET_DATA": str(data_dir)},
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.3)
            return p
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([str(PY), "demo_data.py"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    demo = tmp / "demo"
    shutil.copytree(ROOT / "demo-data", demo)
    import sqlite3
    with sqlite3.connect(demo / "budget.db") as c:  # an account so the Gmail card looks connected
        c.execute("INSERT OR REPLACE INTO settings VALUES ('gmail_accounts', '[\"ban@gmail.com\"]')")
    fresh = tmp / "fresh"
    servers = [serve(demo, 8811), serve(fresh, 8812)]
    try:
        with sync_playwright() as pw:
            b = pw.webkit.launch()
            ctx = b.new_context(viewport={"width": 1180, "height": 1120}, device_scale_factor=2,
                                color_scheme="light", locale="vi-VN")

            def page(url, tab="overview"):
                pg = ctx.new_page()
                pg.goto(f"{url}/#{tab}")
                pg.wait_for_selector("#monthLabel:not(:empty)")
                pg.wait_for_timeout(500)
                return pg

            def snap(pg, name, sel=".modal"):
                pg.wait_for_timeout(400)  # let the open animation finish
                target = pg.locator(sel).first if sel else pg
                target.screenshot(path=str(OUT / f"{name}.png"))

            pg = page("http://127.0.0.1:8812")
            pg.fill("#wName", "Lan")
            snap(pg, "welcome")
            pg.keyboard.press("Escape")
            for step, name in ((0, "wiz1"), (1, "wiz2"), (2, "wiz3")):
                pg.evaluate(f"gmailWizard({step})")
                if step == 2:
                    pg.fill("#wAddr", "ban@gmail.com")
                    pg.fill("#wPass", "abcd efgh ijkl mnop")
                snap(pg, name)
                pg.keyboard.press("Escape")
            pg.close()

            pg = page("http://127.0.0.1:8811")
            snap(pg, "overview", None)
            pg.locator("#addBtn").click()
            pg.fill("#mAmt", "1,5tr")
            pg.locator("#mAmt").dispatch_event("input")
            pg.fill("#mDesc", "Học phí tháng 11 bé An")
            snap(pg, "add")
            pg.keyboard.press("Escape")
            pg.locator("#recent .txrow").nth(3).click()
            pg.locator("#mCats .catchip:not(.on)").nth(4).click()
            snap(pg, "edit")
            pg.keyboard.press("Escape")

            pg.locator("nav button[data-tab=import]").click()
            snap(pg, "import", ".grid3")
            pg.set_input_files("#files", str(ROOT / "demo-data" / "momo" / "momo-2026-10-2.png"))
            pg.wait_for_selector("#ocrRows .ocr-row", timeout=20000)
            snap(pg, "ocr", "#ocrCard")

            pg.locator("nav button[data-tab=recon]").click()
            pg.fill("#stmtForm [name=account]", "Visa Techcombank")
            pg.set_input_files("#stmtInput", str(ROOT / "demo-data" / "sao-ke-visa-thang-10.xlsx"))
            snap(pg, "recon-form", "#recon > .card")
            pg.click("#stmtGo")
            pg.wait_for_selector(".rec-tile")
            pg.wait_for_selector(".toast", state="detached", timeout=8000)
            snap(pg, "recon-tiles", ".rec-tiles")
            snap(pg, "recon-missing", "#recResult > .card:has(h2:has-text('Chưa ghi trong app'))")

            pg.locator("nav button[data-tab=settings]").click()
            snap(pg, "budget", ".catcard:has-text('Mỹ phẩm')")
            pg.locator("nav button[data-tab=overview]").click()
            snap(pg, "categories", "#cats")
            b.close()
    finally:
        for s in servers:
            s.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    shutil.copy(ROOT / "demo-data" / "momo" / "momo-2026-10-1.png", OUT / "momo-sample.png")
    print("screenshots:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
