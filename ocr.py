"""Offline OCR with the macOS Vision framework (Vietnamese supported from macOS 13)."""
import platform

MIN_MACOS = (13, 0)  # Vision has no "vi-VT" before Ventura; the app itself runs from macOS 11


def macos_version() -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in platform.mac_ver()[0].split(".")[:2])
    except ValueError:
        return (0,)


def unsupported_reason() -> str | None:
    """Vietnamese message when this Mac cannot read screenshots, else None."""
    v = macos_version()
    if v >= MIN_MACOS:
        return None
    shown = ".".join(map(str, v)) if v != (0,) else "không rõ"
    return (f"Đọc ảnh cần macOS 13 trở lên (máy này đang chạy macOS {shown}). Hãy nhập tay khoản này "
            "(＋ Thêm khoản), hoặc cập nhật macOS nếu máy hỗ trợ.")


def ocr_rows(path: str) -> list[str]:
    """Text of the image, one string per visual row, top to bottom."""
    reason = unsupported_reason()
    if reason:
        raise RuntimeError(reason)
    rows = _recognize(path, cpu_only=False)
    # Under heavy GPU load Vision has returned nothing for a readable image; one CPU retry is cheap.
    return rows or _recognize(path, cpu_only=True)


def _recognize(path: str, cpu_only: bool) -> list[str]:
    import Vision  # lazily, after the version check: pyobjc is slow to load
    from Foundation import NSURL

    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(NSURL.fileURLWithPath_(path), None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["vi-VT", "en-US"])
    req.setUsesLanguageCorrection_(True)
    if cpu_only:
        req.setUsesCPUOnly_(True)
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
