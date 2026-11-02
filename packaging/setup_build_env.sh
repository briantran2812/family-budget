#!/bin/zsh
# One-time: create .venv-build-arm64 and .venv-build-x86_64 for packaging/build.sh. No admin rights needed.
# CPython comes from python-build-standalone via uv (arm64 targets macOS 11, x86_64 macOS 10.15), so the bundle
# runs on macOS 11+; see docs/DEPLOY.md. Re-run after changing requirements.txt.
set -euo pipefail
cd "${0:A:h}/.."
PYVER=3.12
UV=${UV:-$(command -v uv || echo "$HOME/.local/bin/uv")}
if [[ ! -x $UV ]]; then
  echo "==> installing uv into ~/.local/bin (shell profile left untouched)"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
  UV=$HOME/.local/bin/uv
fi
if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
  echo "Rosetta is missing; the Intel build needs it: softwareupdate --install-rosetta --agree-to-license" >&2
  exit 1
fi
for ARCH in arm64 x86_64; do
  PBS=$([[ $ARCH == arm64 ]] && echo aarch64 || echo x86_64)
  echo "==> $ARCH"
  "$UV" python install "cpython-$PYVER-macos-$PBS-none"
  PYBIN=$("$UV" python find "cpython-$PYVER-macos-$PBS-none")
  "$UV" venv -q --allow-existing --python "$PYBIN" ".venv-build-$ARCH"
  "$UV" pip install -q --python ".venv-build-$ARCH/bin/python" -r requirements.txt \
    pyinstaller==6.22.3 pyinstaller-hooks-contrib==2026.9
  arch -$ARCH ".venv-build-$ARCH/bin/python" -c "import platform, sys; print('   ', platform.machine(), sys.version.split()[0])"
done
