"""Release with a QA gate.

  .venv/bin/python packaging/release.py rc      # tests → build → packaged smoke test → RC .dmg + QA sign-off sheet
  .venv/bin/python packaging/release.py final   # only if the sheet is signed GO for that exact RC file

See docs/RELEASE-PROCESS.md.
"""
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv" / "bin" / "python"
sys.path.insert(0, str(ROOT))
from app import VERSION  # noqa: E402

APP = ROOT / "dist" / "Thu Chi Gia Dinh.app"
RC_DMG = ROOT / "dist" / f"ThuChiGiaDinh-{VERSION}-rc.dmg"
SIGNOFF = ROOT / "qa" / f"QA-SIGNOFF-{VERSION}.md"
REPORTS = ROOT / "qa" / "reports" / VERSION
CASES = ROOT / "docs" / "UX-TEST-CASES.md"


def step(msg):
    print(f"\n==> {msg}", flush=True)


def fail(msg):
    print(f"\n✗ RELEASE BLOCKED: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pytest(name: str, args: list, env=None) -> str:
    REPORTS.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(PY), "-m", "pytest", "-q", f"--junitxml={REPORTS / name}.xml", *args],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    summary = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
    (REPORTS / f"{name}.txt").write_text(r.stdout + r.stderr)
    print(f"    {name}: {summary}")
    if r.returncode:
        fail(f"{name} tests failed — see qa/reports/{VERSION}/{name}.txt")
    return summary


def manual_cases() -> list[tuple[str, str, str]]:
    rows = [ln for ln in CASES.read_text().splitlines() if ln.startswith("| M-")]
    return [tuple(c.strip() for c in ln.strip("|").split("|")[:3]) for ln in rows]


def rc() -> None:
    import os
    step(f"Version {VERSION}: automated tests")
    unit = pytest("unit-integration", ["tests", "--ignore=tests/e2e", "--ignore=tests/test_packaged.py"])
    e2e = pytest("e2e-ux", ["tests/e2e"])

    step("Build")
    subprocess.run([str(ROOT / "packaging" / "build.sh")], cwd=ROOT, check=True)
    shutil.move(ROOT / "dist" / f"ThuChiGiaDinh-{VERSION}.dmg", RC_DMG)

    step("Smoke test of the packaged app")
    packaged = pytest("packaged", ["tests/test_packaged.py"], env={**os.environ, "APP_PATH": str(APP)})

    digest = sha256(RC_DMG)
    step(f"QA sign-off sheet → {SIGNOFF.relative_to(ROOT)}")
    if SIGNOFF.exists() and digest not in SIGNOFF.read_text():
        SIGNOFF.rename(SIGNOFF.with_suffix(f".superseded-{date.today()}.md"))
        print("    a sheet for an older RC build existed — kept as *.superseded-*.md")
    if not SIGNOFF.exists():
        rows = "\n".join(f"| {i} | {p} | {n} | ☐ | |" for i, p, n in manual_cases())
        SIGNOFF.write_text(f"""# QA sign-off — Thu Chi Gia Đình {VERSION}

- RC file: `dist/{RC_DMG.name}`
- SHA-256: `{digest}`
- Built: {date.today()}

## Automated (filled by release.py — do not edit)

| Suite | Result |
| --- | --- |
| Unit + integration + OCR | {unit} |
| End-to-end UX (WebKit) | {e2e} |
| Packaged app smoke test | {packaged} |

Reports: `qa/reports/{VERSION}/`

## Manual (QA fills in)

Test on **the RC file above**, following docs/UX-TEST-CASES.md. In the Result column write
`PASS`, `FAIL`, or `WAIVED: <reason>` (P2 only). Every P1 must be PASS.

| ID | Priority | Case | Result | Notes |
| --- | --- | --- | --- | --- |
{rows}

## Decision

Decision: ☐ GO  ☐ NO-GO
Approved by:
Date:
""")
    print(f"\n✓ RC ready: dist/{RC_DMG.name}\n  Next: run the manual cases on that file, fill {SIGNOFF.relative_to(ROOT)}, "
          f"then `release.py final`.")


def final() -> None:
    step(f"Version {VERSION}: checking QA sign-off")
    if not RC_DMG.exists():
        fail(f"no RC build dist/{RC_DMG.name} — run `release.py rc` first")
    if not SIGNOFF.exists():
        fail(f"no sign-off sheet {SIGNOFF.relative_to(ROOT)}")
    sheet = SIGNOFF.read_text()
    if sha256(RC_DMG) not in sheet:
        fail("the RC file changed after QA signed — QA must re-test this build")

    problems = []
    for ln in sheet.splitlines():
        if not ln.startswith("| M-"):
            continue
        cid, prio, name, result = (c.strip() for c in ln.strip("|").split("|")[:4])
        ok = result == "PASS" or (prio == "P2" and result.startswith("WAIVED:") and len(result) > 8)
        if not ok:
            problems.append(f"{cid} ({prio}) {name}: {result or 'empty'}")
    if problems:
        fail("manual cases not passed:\n  - " + "\n  - ".join(problems))
    if not re.search(r"Decision:.*\[x\]\s*GO|Decision:\s*☑\s*GO|Decision:\s*GO\b", sheet):
        fail("Decision is not GO (write `Decision: GO`)")
    approver = re.search(r"^Approved by:\s*(\S.*)$", sheet, re.M)
    if not approver:
        fail("'Approved by:' is empty")

    out = ROOT / "release"
    out.mkdir(exist_ok=True)
    final_dmg = out / f"ThuChiGiaDinh-{VERSION}.dmg"
    shutil.copy2(RC_DMG, final_dmg)
    (out / f"ThuChiGiaDinh-{VERSION}.sha256").write_text(f"{sha256(final_dmg)}  {final_dmg.name}\n")
    shutil.copy2(SIGNOFF, out / SIGNOFF.name)
    print(f"\n✓ Released {final_dmg.relative_to(ROOT)} (approved by {approver.group(1).strip()})")


if __name__ == "__main__":
    {"rc": rc, "final": final}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
