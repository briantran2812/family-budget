"""Offline OCR with the macOS Vision framework (Vietnamese supported from macOS 13)."""
import Vision
from Foundation import NSURL


def ocr_rows(path: str) -> list[str]:
    """Text of the image, one string per visual row, top to bottom."""
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(NSURL.fileURLWithPath_(path), None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["vi-VT", "en-US"])
    req.setUsesLanguageCorrection_(True)
    ok, err = handler.performRequests_error_([req], None)
    if not ok:
        raise RuntimeError(f"OCR failed: {err}")

    boxes = []
    for obs in req.results() or []:
        cand = obs.topCandidates_(1)
        if not cand:
            continue
        bb = obs.boundingBox()  # normalised, origin bottom-left
        boxes.append((1 - (bb.origin.y + bb.size.height / 2), bb.origin.x, bb.size.height, cand[0].string()))

    # Join boxes whose vertical centres are within half a line height: "Thành tiền:" and "₫120.000"
    # are separate boxes on the same row.
    boxes.sort()
    rows: list[list] = []
    for y, x, h, text in boxes:
        if rows and abs(rows[-1][0] - y) < h / 2:
            rows[-1][1].append((x, text))
        else:
            rows.append([y, [(x, text)]])
    return [" ".join(t for _, t in sorted(parts)) for _, parts in rows]
