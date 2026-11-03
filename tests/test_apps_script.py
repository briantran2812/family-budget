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


@pytest.mark.skipif(not shutil.which("node"), reason="needs Node.js")
def test_code_gs_html_to_text_matches_the_mac_parser():
    """Code.gs sends email bodies as text; it must be the text parsers.html_to_text makes, as on the IMAP path."""
    import json

    import parsers
    from samples import shopee_email
    pages = [shopee_email("261101ABCD1234", [("Kem chống nắng Anessa", 2, 465_000), ("Son & dưỡng", 1, 89_000)], 30_000, 15_000),
             "<div>Tổng&nbsp;cộng:&#160;<b>1.250.000&#x111;</b></div><!-- x --><script>var a = '<td>';</script>"
             "<p>A &lt;b&gt; &amp; c</p><br/>\t<span>  x  </span>",
             "<html><head><title>T</title></head><body><table><tr><th>Mã đơn</th><td>#1</td></tr></table></body></html>"]
    r = subprocess.run(["node", str(HARNESS), "--html-to-text"], input=json.dumps(pages), capture_output=True,
                       text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [parsers.html_to_text(p) for p in pages]
