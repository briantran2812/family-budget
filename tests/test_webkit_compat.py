"""The page must run in macOS 11's WKWebView (≈ Safari 14); the E2E tests use a current WebKit and cannot see this."""
import re
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "static" / "index.html").read_text()

# feature → first Safari version that has it
TOO_NEW = {
    r"\.at\(": "Array/String .at() — Safari 15.4",
    r"\binset\s*:": "CSS inset — Safari 14.1",
    r":has\(": "CSS :has() — Safari 15.4",
    r"\bstructuredClone\(": "structuredClone — Safari 15.4",
    r"\.findLast(Index)?\(": "findLast — Safari 15.4",
    r"Object\.hasOwn\(": "Object.hasOwn — Safari 15.4",
    r"\.(toSorted|toReversed|toSpliced)\(": "change-array-by-copy — Safari 16",
    r"<dialog\b|\.showModal\(": "<dialog> — Safari 15.4",
    r"\.requestSubmit\(": "requestSubmit — Safari 16",
    r"crypto\.randomUUID": "randomUUID — Safari 15.4",
    r"\(\?<[=!]": "regex lookbehind — Safari 16.4",
    r"color-mix\(|@container|\bdvh\b|\bsvh\b": "modern CSS — Safari 15.4+",
    r"aspect-ratio\s*:": "aspect-ratio — Safari 15",
}


def test_no_features_newer_than_safari_14():
    found = [f"{why}: {m.group(0)!r} at line {PAGE.count(chr(10), 0, m.start()) + 1}"
             for pat, why in TOO_NEW.items() for m in re.finditer(pat, PAGE)]
    assert not found, "\n".join(found)
