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


def _node(*args, stdin, env=None):
    import json
    import os
    r = subprocess.run(["node", str(HARNESS), *args], input=json.dumps(stdin, ensure_ascii=False), capture_output=True,
                       text=True, timeout=60, env={**os.environ, **(env or {})})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _custom_rules(conn):
    """A category made on the Mac and keywords with edges the port must treat as Python does."""
    import rules
    cid = conn.execute("INSERT INTO categories(name, kind, sort, icon) VALUES ('Nuôi mèo', 'expense', 99, '🐱')").lastrowid
    for kw in ("pate meo", "cat_tuong", "c++", "sim 4g", "2 nguoi"):
        conn.execute("INSERT INTO rules(keyword, category_id) VALUES (?, ?)", (rules.normalize(kw), cid))


DESCRIPTIONS = [
    "Phở bò tái", "PHỞ BÒ", "phở", "Đi chợ sáng", "ĐỒ ĂN vặt", "Bún chả Hà Nội", "Grab về nhà", "grabfood trưa",
    "grabbike", "Lương tháng 10", "Ăn trưa công ty", "Thưởng công ty", "tiền điện tháng 10", "Học phí  bé An",
    "áo khoác\tmới", "giao hàng bao bì", "mì_tôm", "sim123", "sim 4g", "sim-4g", "H&M", "h&mx", "Pate mèo Whiskas",
    "cat_tuong", "lớp c++ online", "vé 2 người", "x2 người", "  Cà   phê  ", "Ｃà phê", "𝐀ao", "aoᅠ", "đ", "",
    "Thứ gì đó lạ hoắc", "Bánh mì ốp la", "Sữa tươi Vinamilk", "khẩu trang y tế", "Nạp tiền điện thoại",
]


@pytest.mark.skipif(not shutil.which("node"), reason="needs Node.js")
def test_code_gs_categorize_matches_the_mac(conn):
    """The bot picks a category from the keywords the Mac sends; it must be the one rules.categorize would pick."""
    import phone_inbox
    import rules
    _custom_rules(conn)
    payload_rules = phone_inbox.keyword_rules(conn)
    got = _node("--categorize", stdin={"rules": payload_rules, "texts": DESCRIPTIONS})
    name = lambda cid: conn.execute("SELECT name FROM categories WHERE id = ?", (cid,)).fetchone()[0]
    fallback = {"expense": "Khác", "income": "Thu nhập khác"}
    for text, (norm, expense, income) in zip(DESCRIPTIONS, got):
        assert norm == rules.normalize(text), text
        assert (expense or fallback["expense"]) == name(rules.categorize(conn, text, "expense")), text
        assert (income or fallback["income"]) == name(rules.categorize(conn, text, "income")), text
    matched = {text: e for text, (_n, e, _i) in zip(DESCRIPTIONS, got)}
    assert matched["Pate mèo Whiskas"] == "Nuôi mèo" and matched["grabfood trưa"] == "Ăn uống & đi chợ"
    assert matched["grabbike"] == "Đi lại & xăng xe" and matched["giao hàng bao bì"] is None


@pytest.mark.skipif(not shutil.which("node"), reason="needs Node.js")
@pytest.mark.parametrize("version", ["4", "current"])
def test_mac_payload_with_keywords_reaches_code_gs(conn, tmp_path, version):
    """App 1.5.0 adds `rules` to every mirror push: Code.gs 4 (deployed until the user pastes 5) must ignore it."""
    import phone_inbox
    conn.execute("INSERT INTO transactions(date, amount, description) VALUES ('2026-11-02', 45000, 'Phở bò')")
    payload = phone_inbox.mirror_payload(conn)
    env = {}
    if version == "4":
        src = subprocess.run(["git", "show", "8cc57fa:phone/Code.gs"], cwd=HARNESS.parent, capture_output=True, text=True)
        if src.returncode:
            pytest.skip("git history with Code.gs 4 not available")
        (tmp_path / "Code.gs").write_text(src.stdout)
        env["CODE_GS"] = str(tmp_path / "Code.gs")
    got = _node("--mirror", stdin=payload, env=env)
    assert got["reply"] == {"ok": True, "rows": 1, "summary": len(payload["summary"])}
    assert got["tx"] == 1
    if version == "4":
        assert got["version"] == 4 and got["keywords"] is None and got["rules"] is None
    else:
        assert got["keywords"] == len(payload["rules"]) and got["rules"] == payload["rules"]
