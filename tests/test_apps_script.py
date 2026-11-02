"""phone/Code.gs (Google Apps Script) run in Node against fakes of the Google services."""
import shutil
import subprocess
from pathlib import Path

import pytest

HARNESS = Path(__file__).parent / "apps_script" / "harness.mjs"


@pytest.mark.skipif(not shutil.which("node"), reason="needs Node.js")
def test_apps_script():
    r = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
