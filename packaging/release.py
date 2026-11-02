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
# A Mac that sleeps mid-run fires every Playwright timeout at once on wake (seen in 1.3.0 RC); keep it awake.
KEEP_AWAKE = ["caffeinate", "-i"] if sys.platform == "darwin" else []
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


def pytest(name: str, args: list, env=None, timeout: int = 300) -> str:
    """Run one suite in its own process group, so a hang (e.g. a stuck WebKit child) blocks the release
    instead of the terminal — a timeout kills the whole group."""
    import os
    import signal
    REPORTS.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([*KEEP_AWAKE, str(PY), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "faulthandler_timeout=120",
                             f"--junitxml={REPORTS / name}.xml", *args],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
                            start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
        (REPORTS / f"{name}.txt").write_text(out or "")
        fail(f"{name} tests did not finish within {timeout}s — see qa/reports/{VERSION}/{name}.txt")
    summary = (out.strip().splitlines() or ["(no output)"])[-1]
    (REPORTS / f"{name}.txt").write_text(out)
    print(f"    {name}: {summary}")
    if proc.returncode:
        fail(f"{name} tests failed — see qa/reports/{VERSION}/{name}.txt")
    return summary


# Architectures the bundle must run on. Smoke tests only run on the build machine, so a library that needs a
# newer macOS or another CPU passes them and fails on the user's Mac (1.3.0 RC: Homebrew libs required macOS 26).
REQUIRED_ARCHS = {"arm64"}


def check_bundle(app: Path) -> str:
    plist = app / "Contents" / "Info.plist"
    declared = subprocess.run(["/usr/libexec/PlistBuddy", "-c", "Print :LSMinimumSystemVersion", str(plist)],
                              capture_output=True, text=True).stdout.strip() or "0"
    as_tuple = lambda v: tuple(int(x) for x in v.split("."))
    too_new, missing_arch = [], []
    for f in app.rglob("*"):
        if not f.is_file() or f.is_symlink() or not (f.suffix in (".so", ".dylib") or f.stat().st_mode & 0o111):
            continue
        archs = subprocess.run(["lipo", "-archs", str(f)], capture_output=True, text=True)
        if archs.returncode:
            continue  # not a Mach-O file
        if not REQUIRED_ARCHS <= set(archs.stdout.split()):
            missing_arch.append(f"{f.name} ({archs.stdout.strip()})")
        load = subprocess.run(["otool", "-l", str(f)], capture_output=True, text=True).stdout
        mins = re.findall(r"LC_BUILD_VERSION[\s\S]*?minos (\S+)", load) + \
            re.findall(r"LC_VERSION_MIN_MACOSX[\s\S]*?version (\S+)", load)
        for m in mins:
            if as_tuple(m) > as_tuple(declared):
                too_new.append(f"{f.name} needs macOS {m}")
    if too_new or missing_arch:
        fail(f"bundle does not run on what Info.plist promises (macOS {declared}, {sorted(REQUIRED_ARCHS)}):\n  - "
             + "\n  - ".join(sorted(set(too_new))[:15] + missing_arch[:15]))
    return f"macOS ≥ {declared}, {'+'.join(sorted(REQUIRED_ARCHS))}"


def manual_cases() -> list[tuple[str, str, str]]:
    rows = [ln for ln in CASES.read_text().splitlines() if ln.startswith("| M-")]
    return [tuple(c.strip() for c in ln.strip("|").split("|")[:3]) for ln in rows]


def rc() -> None:
    import os
    # Retire the previous RC and its sheet first: if this run is blocked, nothing stale may still look releasable.
    for old in (RC_DMG, SIGNOFF):
        if old.exists():
            old.rename(old.with_name(f"{old.stem}.stale-{date.today()}{old.suffix}"))
            print(f"    retired {old.relative_to(ROOT)}")
    step(f"Version {VERSION}: automated tests")
    unit = pytest("unit-integration", ["tests", "--ignore=tests/e2e", "--ignore=tests/test_packaged.py"])
    e2e = pytest("e2e-ux", ["tests/e2e"])

    step("Build")
    subprocess.run([*KEEP_AWAKE, str(ROOT / "packaging" / "build.sh")], cwd=ROOT, check=True)
    shutil.move(ROOT / "dist" / f"ThuChiGiaDinh-{VERSION}.dmg", RC_DMG)

    step("Bundle compatibility (CPU architectures, minimum macOS)")
    compat = check_bundle(APP)
    print(f"    {compat}")

    step("Smoke test of the packaged app")
    packaged = pytest("packaged", ["tests/test_packaged.py"], env={**os.environ, "APP_PATH": str(APP)})

    digest = sha256(RC_DMG)
    step(f"QA sign-off sheet → {SIGNOFF.relative_to(ROOT)}")
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
| Bundle compatibility | {compat} |
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


def require_release_branch() -> None:
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if branch != "develop" and not branch.startswith("release/"):
        fail(f"release builds come from `develop` or `release/…`, not `{branch}` — merge the work first "
             "(docs/RELEASE-PROCESS.md, Nhánh git)")
    if subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                      capture_output=True, text=True).stdout.strip():
        fail("uncommitted changes — QA must test a build that matches a commit")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("rc", "final"):
        require_release_branch()
    {"rc": rc, "final": final}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
