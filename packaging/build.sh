#!/bin/zsh
# Build "Thu Chi Gia Dinh.app" (Python bundled inside) and a .dmg to send to family.
# Output: dist/ThuChiGiaDinh-<version>.dmg
set -euo pipefail
cd "${0:A:h}/.."
PY=.venv/bin/python
NAME="Thu Chi Gia Dinh"
VERSION=$($PY -c "import app; print(app.VERSION)")

$PY packaging/make_icon.py
rm -rf build dist
.venv/bin/pyinstaller --noconfirm --windowed --log-level WARN \
  --name "$NAME" --icon packaging/AppIcon.icns \
  --osx-bundle-identifier vn.family.thuchi \
  --add-data "static:static" \
  --add-data "phone/Code.gs:phone" \
  --hidden-import keyring.backends.macOS \
  desktop.py

PLIST="dist/$NAME.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 13.0" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string Thu Chi Gia Đình" "$PLIST" 2>/dev/null || true
codesign --force --deep --sign - "dist/$NAME.app"   # ad-hoc: no Apple account; first open needs "Open Anyway"

STAGE=$(mktemp -d)
cp -R "dist/$NAME.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/HUONG-DAN.txt "$STAGE/Hướng dẫn cài đặt.txt"
hdiutil create -quiet -volname "Thu Chi Gia Đình" -srcfolder "$STAGE" -ov -format UDZO "dist/ThuChiGiaDinh-$VERSION.dmg"
rm -rf "$STAGE"
ls -lh "dist/ThuChiGiaDinh-$VERSION.dmg"
