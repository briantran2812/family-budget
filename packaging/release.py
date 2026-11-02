"""Release with a QA gate.

  .venv/bin/python packaging/release.py rc      # tests → build both archs → packaged smoke tests → RC .dmgs + QA sign-off sheet
  .venv/bin/python packaging/release.py final   # only if the sheet is signed GO for those exact RC files

One build per CPU: arm64 (Apple chip) and x86_64 (Intel, built under Rosetta), both for macOS 11+.

See docs/RELEASE-PROCESS.md.
"""
import hashlib
import platform
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

ARCHS = ("arm64", "x86_64")
CHIP = {"arm64": "Apple chip (M1, M2…)", "x86_64": "Intel"}


def app_path(arch: str) -> Path:
    return ROOT / "dist" / arch / "Thu Chi Gia Dinh.app"


def rc_dmg(arch: str) -> Path:
    return ROOT / "dist" / f"ThuChiGiaDinh-{VERSION}-rc-{arch}.dmg"


def final_dmg(arch: str) -> Path:
    return ROOT / "release" / f"ThuChiGiaDinh-{VERSION}-{arch}.dmg"


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


# Smoke tests only run on the build machine, so a library that needs a newer macOS or another CPU passes them
# and fails on the user's Mac (1.3.0 RC: Homebrew libs required macOS 26). Each build must carry its own arch.
def check_bundle(app: Path, arch: str) -> str:
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
        if arch not in archs.stdout.split():
            missing_arch.append(f"{f.name} ({archs.stdout.strip()})")
            continue
        # Only the slice that will run matters: universal pyobjc wheels have a different minos per slice.
        load = subprocess.run(["otool", "-arch", arch, "-l", str(f)], capture_output=True, text=True).stdout
        mins = re.findall(r"LC_BUILD_VERSION[\s\S]*?minos (\S+)", load) + \
            re.findall(r"LC_VERSION_MIN_MACOSX[\s\S]*?version (\S+)", load)
        for m in mins:
            if as_tuple(m) > as_tuple(declared):
                too_new.append(f"{f.name} needs macOS {m}")
    if too_new or missing_arch:
        fail(f"{arch} bundle does not run on what Info.plist promises (macOS {declared}, {arch}):\n  - "
             + "\n  - ".join(sorted(set(too_new))[:15] + missing_arch[:15]))
    return f"{arch}: macOS ≥ {declared}"


def can_run(arch: str) -> bool:
    """x86_64 runs here under Rosetta; arm64 never runs on an Intel build machine."""
    return subprocess.run(["arch", f"-{arch}", "/usr/bin/true"], capture_output=True).returncode == 0


def manual_cases() -> list[tuple[str, str, str]]:
    rows = [ln for ln in CASES.read_text().splitlines() if ln.startswith("| M-")]
    return [tuple(c.strip() for c in ln.strip("|").split("|")[:3]) for ln in rows]


def rc() -> None:
    import os
    # Retire the previous RC and its sheet first: if this run is blocked, nothing stale may still look releasable.
    for old in (*map(rc_dmg, ARCHS), SIGNOFF):
        if old.exists():
            old.rename(old.with_name(f"{old.stem}.stale-{date.today()}{old.suffix}"))
            print(f"    retired {old.relative_to(ROOT)}")
    step(f"Version {VERSION}: automated tests")
    unit = pytest("unit-integration", ["tests", "--ignore=tests/e2e", "--ignore=tests/test_packaged.py"])
    e2e = pytest("e2e-ux", ["tests/e2e"])

    compat, packaged = {}, {}
    for arch in ARCHS:
        step(f"Build {arch} ({CHIP[arch]})")
        subprocess.run([*KEEP_AWAKE, str(ROOT / "packaging" / "build.sh"), arch], cwd=ROOT, check=True)
        shutil.move(ROOT / "dist" / f"ThuChiGiaDinh-{VERSION}-{arch}.dmg", rc_dmg(arch))

        step(f"Bundle compatibility {arch} (CPU architecture, minimum macOS)")
        compat[arch] = check_bundle(app_path(arch), arch)
        print(f"    {compat[arch]}")

    for arch in ARCHS:
        step(f"Smoke test of the packaged app, {arch}" + (" (Rosetta)" if arch != platform.machine() else ""))
        if not can_run(arch):
            if arch == platform.machine():
                fail(f"cannot run the native {arch} build")
            packaged[arch] = "not run: this Mac cannot run it (M-01 on such a Mac covers it)"
            print(f"    {packaged[arch]}")
            continue
        packaged[arch] = pytest(f"packaged-{arch}", ["tests/test_packaged.py"],
                                env={**os.environ, "APP_PATH": str(app_path(arch))})

    digests = {arch: sha256(rc_dmg(arch)) for arch in ARCHS}
    step(f"QA sign-off sheet → {SIGNOFF.relative_to(ROOT)}")
    if not SIGNOFF.exists():
        rows = "\n".join(f"| {i} | {p} | {n} | ☐ | |" for i, p, n in manual_cases())
        SIGNOFF.write_text(f"""# QA sign-off — Thu Chi Gia Đình {VERSION}

- Built: {date.today()}

| CPU | RC file | SHA-256 |
| --- | --- | --- |
{chr(10).join(f"| {CHIP[a]} | `dist/{rc_dmg(a).name}` | `{digests[a]}` |" for a in ARCHS)}

## Automated (filled by release.py — do not edit)

| Suite | Result |
| --- | --- |
| Unit + integration + OCR | {unit} |
| End-to-end UX (WebKit) | {e2e} |
{chr(10).join(f"| Bundle compatibility {a} | {compat[a]} |" for a in ARCHS)}
{chr(10).join(f"| Packaged app smoke test {a} | {packaged[a]} |" for a in ARCHS)}

Reports: `qa/reports/{VERSION}/`

## Manual (QA fills in)

Test on **the RC files above** (M-01 on the chip of the Mac it will be delivered to), following docs/UX-TEST-CASES.md. In the Result column write
`PASS`, `FAIL`, or `WAIVED: <reason>` (P2 only). Every P1 must be PASS.

| ID | Priority | Case | Result | Notes |
| --- | --- | --- | --- | --- |
{rows}

## Decision

Decision: ☐ GO  ☐ NO-GO
Approved by:
Date:
""")
    print(f"\n✓ RC ready: " + ", ".join(f"dist/{rc_dmg(a).name}" for a in ARCHS) +
          f"\n  Next: run the manual cases on those files, fill {SIGNOFF.relative_to(ROOT)}, then `release.py final`.")


def final() -> None:
    step(f"Version {VERSION}: checking QA sign-off")
    for arch in ARCHS:
        if not rc_dmg(arch).exists():
            fail(f"no RC build dist/{rc_dmg(arch).name} — run `release.py rc` first")
    if not SIGNOFF.exists():
        fail(f"no sign-off sheet {SIGNOFF.relative_to(ROOT)}")
    sheet = SIGNOFF.read_text()
    for arch in ARCHS:
        if sha256(rc_dmg(arch)) not in sheet:
            fail(f"the {arch} RC file changed after QA signed — QA must re-test this build")

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
    out.mkdir(exist_ok=True)  # older versions stay here: rollback = reinstall the previous DMG (docs/DEPLOY.md F)
    sums = []
    for arch in ARCHS:
        shutil.copy2(rc_dmg(arch), final_dmg(arch))
        sums.append(f"{sha256(final_dmg(arch))}  {final_dmg(arch).name}\n")
    (out / f"ThuChiGiaDinh-{VERSION}.sha256").write_text("".join(sums))
    shutil.copy2(SIGNOFF, out / SIGNOFF.name)
    print(f"\n✓ Released " + ", ".join(str(final_dmg(a).relative_to(ROOT)) for a in ARCHS) +
          f" (approved by {approver.group(1).strip()})")


def require_release_branch() -> None:
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if branch != "develop" and not branch.startswith("release/"):
        fail(f"release builds come from `develop` or `release/…`, not `{branch}` — merge the work first "
             "(docs/RELEASE-PROCESS.md, Nhánh git)")
    if subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                      capture_output=True, text=True).stdout.strip():
        fail("uncommitted changes — QA must test a build that matches a commit")


def check() -> None:
    """`release.py check [arch…]`: check_bundle on apps already built by build.sh; allowed on any branch."""
    for arch in sys.argv[2:] or ARCHS:
        print(check_bundle(app_path(arch), arch))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("rc", "final"):
        require_release_branch()
    {"rc": rc, "final": final, "check": check}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
