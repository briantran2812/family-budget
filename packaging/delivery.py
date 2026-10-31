"""Assemble delivery/ThuChiGiaDinh-<ver>/: user guide PDF + installer, and a .zip of it for Zalo.

  .venv/bin/python packaging/delivery.py          # uses the RC (for QA field testing)
  .venv/bin/python packaging/delivery.py --final  # uses release/ (after `release.py final`)
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "packaging" / "guide"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sys.path.insert(0, str(ROOT))
from app import VERSION  # noqa: E402


def main() -> None:
    final = "--final" in sys.argv
    dmg = ROOT / "release" / f"ThuChiGiaDinh-{VERSION}.dmg" if final else ROOT / "dist" / f"ThuChiGiaDinh-{VERSION}-rc.dmg"
    if not dmg.exists():
        sys.exit(f"missing {dmg.relative_to(ROOT)} — run packaging/release.py {'final' if final else 'rc'} first")

    sheet = ROOT / "qa" / f"QA-SIGNOFF-{VERSION}.md"
    if not sheet.exists() or hashlib.sha256(dmg.read_bytes()).hexdigest() not in sheet.read_text():
        sys.exit(f"{dmg.name} is not the build recorded in {sheet.name} — run `release.py rc` (it must pass) first")
    subprocess.run(["caffeinate", "-i", str(ROOT / ".venv" / "bin" / "python"), str(GUIDE / "shoot.py")], check=True)
    label = VERSION if final else f"{VERSION} thử nghiệm"
    html = (GUIDE / "guide.html").read_text().replace("{{VERSION}}", label).replace("{{DATE}}", date.today().strftime("%d/%m/%Y"))
    if final:
        html = html.replace(" (bản thử nghiệm)", "")
    with tempfile.TemporaryDirectory() as tmp:
        page = GUIDE / "_render.html"  # next to img/ so relative paths resolve
        page.write_text(html)
        pdf = Path(tmp) / "guide.pdf"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={tmp}/chrome", f"--print-to-pdf={pdf}", page.as_uri()],
                       check=True, capture_output=True)
        page.unlink()

        out = ROOT / "delivery" / f"ThuChiGiaDinh-{VERSION}"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        shutil.copy2(pdf, out / "1. Hướng dẫn sử dụng.pdf")
        shutil.copy2(dmg, out / f"2. File cài đặt - Thu Chi Gia Đình {label}.dmg")

    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()
    zip_path = out.parent / f"{out.name}.zip"  # not with_suffix: it would eat the ".0" of the version
    zip_path.unlink(missing_ok=True)
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(out), str(zip_path)], check=True)
    print(f"✓ {out.relative_to(ROOT)}/  and  {zip_path.relative_to(ROOT)}")
    print(f"  installer SHA-256 {digest}")


if __name__ == "__main__":
    main()
