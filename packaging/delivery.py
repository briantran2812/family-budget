"""Assemble delivery/ThuChiGiaDinh-<ver>/ for the production Mac + family iPhones, and a .zip of it for Zalo/AirDrop.

  .venv/bin/python packaging/delivery.py                  # uses the RC (for QA field testing)
  .venv/bin/python packaging/delivery.py --final          # uses release/ (after `release.py final`)
  .venv/bin/python packaging/delivery.py --final --no-pdf # skip the guide PDF (needs Chrome + Playwright WebKit)

Contents: guide PDF, one installer per chip, install notes, the signed production Shortcut + CAI-DAT-IPHONE.txt,
and Code.gs. Only the build whose SHA-256 is in the signed QA sheet is packaged. See docs/DEPLOY.md D.
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
PY = ROOT / ".venv" / "bin" / "python"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packaging"))
from app import VERSION  # noqa: E402
from release import ARCHS, final_dmg, rc_dmg  # noqa: E402

CHIP_LABEL = {"arm64": "máy chip Apple (M1, M2, M3…)", "x86_64": "máy chip Intel"}

IPHONE_TXT = """CÀI PHÍM TẮT "GHI CHI TIÊU" LÊN IPHONE

Phím tắt gửi khoản chi vào Google Sheet "Thu Chi — PRODUCTION"; app trên Mac tự lấy về mỗi lần mở.

1. Trên Mac: app Thu Chi Gia Đình → Cài đặt → iPhone (Google Sheet) → "📋 Sao chép mã cho iPhone".
   iPhone cùng Apple ID thì dán thẳng được (Universal Clipboard). iPhone khác Apple ID: AirDrop một ghi chú
   chứa mã, dán xong thì xoá ghi chú. Không gửi mã qua nhóm Zalo.
2. AirDrop file "Ghi chi tiêu.shortcut" sang iPhone. iPhone tự mở app Phím tắt.
3. Bấm "Thêm phím tắt". Ô "Dán mã kết nối" hiện ra: chạm và giữ → Dán → Thêm.
4. Chạy thử: gõ 1000, mô tả "thử", chọn Tiền mặt. Lần đầu iOS hỏi cho phép kết nối tới script.google.com
   (và có thể script.googleusercontent.com): chọn "Luôn cho phép".
   Thấy "✓ Đã ghi 1.000 ₫ · thử" là xong. Trên Mac bấm ↻ Đồng bộ, rồi xoá khoản thử.
5. Mở nhanh (chọn một): Cài đặt → Trợ năng → Cảm ứng → Chạm vào mặt sau → Chạm hai lần → Ghi chi tiêu;
   hoặc giữ phím tắt trong app Phím tắt → Chia sẻ → Thêm vào MH chính.

Gõ đủ số tiền, ví dụ 45000 (câu hỏi sau hiện lại 45.000 ₫ để kiểm tra).
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def guide_pdf(label: str, final: bool, tmp: str) -> Path:
    subprocess.run(["caffeinate", "-i", str(PY), str(GUIDE / "shoot.py")], check=True)
    html = (GUIDE / "guide.html").read_text().replace("{{VERSION}}", label).replace("{{DATE}}", date.today().strftime("%d/%m/%Y"))
    if final:
        html = html.replace(" (bản thử nghiệm)", "")
    page = GUIDE / "_render.html"  # next to img/ so relative paths resolve
    page.write_text(html)
    pdf = Path(tmp) / "guide.pdf"
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={tmp}/chrome", f"--print-to-pdf={pdf}", page.as_uri()],
                       check=True, capture_output=True)
    finally:
        page.unlink()
    return pdf


def main() -> None:
    final = "--final" in sys.argv
    dmgs = {a: final_dmg(a) if final else rc_dmg(a) for a in ARCHS}
    for dmg in dmgs.values():
        if not dmg.exists():
            sys.exit(f"missing {dmg.relative_to(ROOT)} — run packaging/release.py {'final' if final else 'rc'} first")

    sheet = ROOT / "qa" / f"QA-SIGNOFF-{VERSION}.md"
    text = sheet.read_text() if sheet.exists() else ""
    for dmg in dmgs.values():
        if sha256(dmg) not in text:
            sys.exit(f"{dmg.name} is not the build recorded in {sheet.name} — run `release.py rc` (it must pass) first")

    step = subprocess.run([str(PY), str(ROOT / "phone" / "make_shortcut.py")])  # production variant, freshly signed
    shortcut = ROOT / "phone" / "dist" / "Ghi chi tiêu.shortcut"
    if step.returncode or not shortcut.exists():
        sys.exit("could not sign the iPhone Shortcut (needs iCloud sign-in and network) — see phone/README.md C")

    label = VERSION if final else f"{VERSION} thử nghiệm"
    out = ROOT / "delivery" / f"ThuChiGiaDinh-{VERSION}"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        if "--no-pdf" not in sys.argv:
            shutil.copy2(guide_pdf(label, final, tmp), out / "1. Hướng dẫn sử dụng.pdf")
    for arch, dmg in dmgs.items():
        shutil.copy2(dmg, out / f"2. File cài đặt - {CHIP_LABEL[arch]} - Thu Chi Gia Đình {label}.dmg")
    shutil.copy2(ROOT / "packaging" / "HUONG-DAN.txt", out / "3. Hướng dẫn cài đặt.txt")
    iphone = out / "4. iPhone"
    iphone.mkdir()
    shutil.copy2(shortcut, iphone / shortcut.name)
    (iphone / "CAI-DAT-IPHONE.txt").write_text(IPHONE_TXT)
    tech = out / "5. Cho người cài đặt"
    tech.mkdir()
    shutil.copy2(ROOT / "phone" / "Code.gs", tech / "Code.gs")
    (tech / "SHA256.txt").write_text("".join(f"{sha256(d)}  {d.name}\n" for d in dmgs.values()))

    zip_path = out.parent / f"{out.name}.zip"  # not with_suffix: it would eat the ".0" of the version
    zip_path.unlink(missing_ok=True)
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(out), str(zip_path)], check=True)
    print(f"✓ {out.relative_to(ROOT)}/  and  {zip_path.relative_to(ROOT)}")
    for dmg in dmgs.values():
        print(f"  {dmg.name}  SHA-256 {sha256(dmg)}")


if __name__ == "__main__":
    main()
