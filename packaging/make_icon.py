"""Draw the app icon (gradient squircle + ₫) and write packaging/AppIcon.icns."""
import subprocess
import sys
import tempfile
from pathlib import Path

from AppKit import (NSBezierPath, NSBitmapImageRep, NSColor, NSFont, NSFontAttributeName,
                    NSForegroundColorAttributeName, NSGradient, NSImage, NSMakePoint, NSMakeRect, NSMakeSize,
                    NSPNGFileType, NSString)

OUT = Path(__file__).parent / "AppIcon.icns"


def draw(px: int, path: Path) -> None:
    img = NSImage.alloc().initWithSize_(NSMakeSize(px, px))
    img.lockFocus()
    inset = px * 0.09
    rect = NSMakeRect(inset, inset, px - 2 * inset, px - 2 * inset)
    shape = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, px * 0.2, px * 0.2)
    grad = NSGradient.alloc().initWithColors_([
        NSColor.colorWithRed_green_blue_alpha_(0.36, 0.31, 0.96, 1),
        NSColor.colorWithRed_green_blue_alpha_(0.55, 0.36, 0.96, 1),
        NSColor.colorWithRed_green_blue_alpha_(0.88, 0.33, 0.61, 1)])
    grad.drawInBezierPath_angle_(shape, -45)
    font = NSFont.systemFontOfSize_weight_(px * 0.5, 0.6)
    attrs = {NSFontAttributeName: font, NSForegroundColorAttributeName: NSColor.whiteColor()}
    s = NSString.stringWithString_("₫")
    size = s.sizeWithAttributes_(attrs)
    s.drawAtPoint_withAttributes_(NSMakePoint((px - size.width) / 2, (px - size.height) / 2 + px * 0.01), attrs)
    img.unlockFocus()
    rep = NSBitmapImageRep.imageRepWithData_(img.TIFFRepresentation())
    rep.representationUsingType_properties_(NSPNGFileType, None).writeToFile_atomically_(str(path), True)


with tempfile.TemporaryDirectory() as tmp:
    iconset = Path(tmp) / "AppIcon.iconset"
    iconset.mkdir()
    for base in (16, 32, 128, 256, 512):
        draw(base, iconset / f"icon_{base}x{base}.png")
        draw(base * 2, iconset / f"icon_{base}x{base}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(OUT)], check=True)
print(OUT, file=sys.stderr)
