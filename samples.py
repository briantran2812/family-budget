"""Fake Shopee/TikTok order emails and MoMo receipt images — shared by demo_data.py and the tests."""
import random
from pathlib import Path

PRODUCTS = [  # (name, base price) — prices jitter ±20%
    ("Kem chống nắng Anessa Perfect UV 60ml", 465_000), ("Son kem lì Romand Juicy Lasting Tint", 189_000),
    ("Serum Vitamin C Klairs 35ml", 329_000), ("Sữa rửa mặt CeraVe Foaming 236ml", 355_000),
    ("Nước tẩy trang Bioderma 500ml", 389_000), ("Mặt nạ dưỡng ẩm Innisfree hộp 10 miếng", 150_000),
    ("Nước giặt Omo Matic cửa trước 3.6kg", 219_000), ("Nước rửa chén Sunlight 3.6kg", 109_000),
    ("Giấy vệ sinh Bless You 10 cuộn", 89_000), ("Hộp đựng thực phẩm Lock&Lock bộ 6", 299_000),
    ("Bỉm quần Bobby size L 68 miếng", 345_000), ("Sữa công thức Meiji số 9 800g", 525_000),
    ("Đồ chơi xếp hình Lego Duplo", 690_000), ("Áo thun cotton nam basic", 159_000),
    ("Váy hoa dáng xoè nữ", 289_000), ("Dép sandal quai ngang", 199_000),
    ("Hạt điều rang muối 500g", 185_000), ("Cà phê hạt rang xay 1kg", 249_000),
    ("Tai nghe bluetooth Soundpeats", 459_000), ("Cáp sạc Type-C Anker 1.8m", 165_000),
    ("Vitamin tổng hợp Centrum 100 viên", 520_000), ("Khẩu trang y tế 4 lớp hộp 50 cái", 45_000),
]

# MoMo bills: (service line, provider, base amount, jitter)
BILLS = [
    ("Học phí tháng {m} - bé An", "Trường Mầm non Hoa Sen", 6_500_000, 0),
    ("Tiền điện EVN HCMC kỳ tháng {m}", "Tổng công ty Điện lực TP.HCM", 1_450_000, 0.25),
    ("Tiền nước Sawaco kỳ tháng {m}", "Cấp nước Gia Định", 320_000, 0.2),
    ("Cước internet FPT tháng {m}", "FPT Telecom", 280_000, 0),
]


def jitter(v: int, pct: float) -> int:
    return int(round(v * random.uniform(1 - pct, 1 + pct), -3))


# ---------------------------------------------------------------- fake order emails

def shopee_email(order_id: str, items: list, ship: int, voucher: int) -> str:
    rows = "".join(f"<tr><td>{n}</td><td>x{q}</td><td>₫{p * q:,}</td></tr>".replace(",", ".") for n, q, p in items)
    total = sum(p * q for _, q, p in items) + ship - voucher
    return f"""<html><body><table>
      <tr><td>Xin chào,</td></tr><tr><td>Đơn hàng #{order_id} của bạn đã được đặt thành công.</td></tr>
      {rows}
      <tr><td>Phí vận chuyển</td><td>₫{ship:,}</td></tr><tr><td>Voucher của Shop</td><td>-₫{voucher:,}</td></tr>
      <tr><td>Tổng thanh toán</td><td>₫{total:,}</td></tr>
      <tr><td>Phương thức thanh toán: ShopeePay</td></tr></table></body></html>""".replace(",", ".")


def tiktok_email(order_id: str, items: list) -> str:
    lines = "\n".join(f"{n}\nSố lượng: {q}\n{p * q:,}đ".replace(",", ".") for n, q, p in items)
    total = sum(p * q for _, q, p in items)
    return f"Order ID: {order_id}\nCảm ơn bạn đã mua sắm trên TikTok Shop!\n{lines}\nPhí vận chuyển 0đ\n" \
           f"Tổng cộng {total:,}đ".replace(",", ".")


# ---------------------------------------------------------------- fake MoMo receipt images

def momo_receipt(path: Path, service: str, provider: str, amount: int, when: str, txid: str) -> None:
    receipt_image(path, "Ví MoMo", (0.65, 0.0, 0.39), "Giao dịch thành công", amount,
                  [("Dịch vụ", service), ("Nhà cung cấp", provider), ("Số tiền", f"{amount:,}đ".replace(",", ".")),
                   ("Phí giao dịch", "Miễn phí"), ("Nguồn tiền", "Ví MoMo"), ("Thời gian", when),
                   ("Mã giao dịch", txid)])


def bank_receipt(path: Path, bank: str, receiver: str, content: str, amount: int, when: str, txid: str) -> None:
    """A generic bank-app transfer confirmation (labels as Vietnamese banking apps show them)."""
    receipt_image(path, bank, (0.0, 0.42, 0.33), "Chuyển khoản thành công", amount,
                  [("Số tiền", f"{amount:,} VND".replace(",", ".")), ("Người nhận", receiver),
                   ("Nội dung", content), ("Thời gian", when), ("Mã giao dịch", txid)])


def receipt_image(path: Path, header: str, rgb: tuple, title: str, amount: int, rows: list) -> None:
    from AppKit import (NSBezierPath, NSBitmapImageRep, NSColor, NSFont, NSFontAttributeName,
                        NSForegroundColorAttributeName, NSImage, NSMakePoint, NSMakeRect, NSMakeSize,
                        NSPNGFileType, NSRectFill, NSString)
    W, H = 720, 1080
    img = NSImage.alloc().initWithSize_(NSMakeSize(W, H))
    img.lockFocus()
    NSColor.colorWithRed_green_blue_alpha_(0.97, 0.96, 0.97, 1).set(); NSRectFill(NSMakeRect(0, 0, W, H))
    NSColor.colorWithRed_green_blue_alpha_(*rgb, 1).set(); NSRectFill(NSMakeRect(0, H - 120, W, 120))

    def text(s, x, y, size, color=None, bold=False):
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        NSString.stringWithString_(s).drawAtPoint_withAttributes_(
            NSMakePoint(x, y), {NSFontAttributeName: font,
                                NSForegroundColorAttributeName: color or NSColor.blackColor()})

    def right(s, y, size, bold=False):
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        w = NSString.stringWithString_(s).sizeWithAttributes_({NSFontAttributeName: font}).width
        text(s, W - 60 - w, y, size, bold=bold)

    text(header, 40, H - 78, 32, NSColor.whiteColor(), bold=True)
    text("DEMO", W - 140, H - 74, 24, NSColor.colorWithWhite_alpha_(1, 0.6), bold=True)
    NSColor.whiteColor().set()
    NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(NSMakeRect(30, 120, W - 60, H - 290), 24, 24).fill()
    text("✓  " + title, 60, H - 230, 30, NSColor.colorWithRed_green_blue_alpha_(0.1, 0.65, 0.35, 1), bold=True)
    text(f"-{amount:,}đ".replace(",", "."), 60, H - 310, 52, bold=True)
    gray = NSColor.colorWithWhite_alpha_(0.45, 1)
    y = H - 410
    for label, value in rows:
        text(label, 60, y, 22, gray)
        right(value, y, 22, bold=label == "Số tiền")
        y -= 64
    img.unlockFocus()
    rep = NSBitmapImageRep.imageRepWithData_(img.TIFFRepresentation())
    rep.representationUsingType_properties_(NSPNGFileType, None).writeToFile_atomically_(str(path), True)
