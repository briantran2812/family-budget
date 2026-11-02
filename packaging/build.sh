#!/bin/zsh
# Build "Thu Chi Gia Dinh.app" (Python bundled inside) and a .dmg to send to family, for one CPU architecture.
#   packaging/build.sh arm64     → dist/arm64/Thu Chi Gia Dinh.app + dist/ThuChiGiaDinh-<ver>-arm64.dmg   (Apple chip)
#   packaging/build.sh x86_64    → dist/x86_64/…                    + dist/ThuChiGiaDinh-<ver>-x86_64.dmg  (Intel, built under Rosetta)
# Each arch uses its own venv (.venv-build-<arch>) on a python-build-standalone CPython that targets macOS 11;
# Homebrew's Python targets the build machine's macOS and made 1.3.0 unusable on older Macs (QA S1).
# Create the venvs once with packaging/setup_build_env.sh.
set -euo pipefail
cd "${0:A:h}/.."
ROOT=$PWD
ARCH=${1:-}
case "$ARCH" in
  arm64|x86_64) ;;
  *) echo "usage: packaging/build.sh arm64|x86_64" >&2; exit 2 ;;
esac
MIN_MACOS=11.0
VENV=$ROOT/.venv-build-$ARCH
PY=$VENV/bin/python
if [[ ! -x $PY ]]; then
  echo "missing $VENV — run packaging/setup_build_env.sh first" >&2; exit 1
fi
RUN=(arch -$ARCH)   # x86_64 runs under Rosetta; also makes sure an arm64 build never picks an x86_64 slice
if [[ $($RUN $PY -c "import platform; print(platform.machine())") != "$ARCH" ]]; then
  echo "$VENV is not a $ARCH Python" >&2; exit 1
fi
NAME="Thu Chi Gia Dinh"
VERSION=$($RUN $PY -c "import app; print(app.VERSION)")
DIST=$ROOT/dist/$ARCH
WORK=$ROOT/build/$ARCH

# The icon is committed; regenerating it on every build left the tree dirty, which blocks `release.py final`.
[[ -f packaging/AppIcon.icns ]] || $RUN $PY packaging/make_icon.py
rm -rf "$WORK" "$DIST"
# Absolute paths: with --specpath, PyInstaller resolves relative data paths against the spec's folder.
MACOSX_DEPLOYMENT_TARGET=$MIN_MACOS $RUN $VENV/bin/pyinstaller --noconfirm --windowed --log-level WARN \
  --distpath "$DIST" --workpath "$WORK" --specpath "$WORK" --target-arch "$ARCH" \
  --name "$NAME" --icon "$ROOT/packaging/AppIcon.icns" \
  --osx-bundle-identifier vn.family.thuchi \
  --add-data "$ROOT/static:static" \
  --add-data "$ROOT/phone/Code.gs:phone" \
  --hidden-import keyring.backends.macOS \
  "$ROOT/desktop.py"

APP="$DIST/$NAME.app"
PLIST="$APP/Contents/Info.plist"
plist_set() {  # Set, or Add when the key is missing
  /usr/libexec/PlistBuddy -c "Set :$1 $3" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :$1 $2 $3" "$PLIST"
}
plist_set CFBundleShortVersionString string "$VERSION"
plist_set LSMinimumSystemVersion string "$MIN_MACOS"
plist_set NSHumanReadableCopyright string "Thu Chi Gia Đình"
codesign --force --deep --sign - "$APP"   # ad-hoc: no Apple account; first open needs "Open Anyway"

DMG="$ROOT/dist/ThuChiGiaDinh-$VERSION-$ARCH.dmg"
STAGE=$(mktemp -d)
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/HUONG-DAN.txt "$STAGE/Hướng dẫn cài đặt.txt"
hdiutil create -quiet -volname "Thu Chi Gia Đình" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"
ls -lh "$DMG"
