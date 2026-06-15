#!/usr/bin/env bash
# ============================================================================
# packaging/build_linux.sh - build a portable Linux tarball.
# ============================================================================
# From the repo root:   bash packaging/build_linux.sh
# Produces:             dist/MirrorZ-Hecras-<version>-linux-x86_64.tar.gz
#
# Linux users typically prefer pip/pipx or a distro package, but a tarball
# of the frozen app is the zero-dependency option for classroom machines.
# ### TODO ###: AppImage and Flatpak recipes are the natural next step for
# store-like distribution on Linux (Flathub). See docs/packaging.md.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

APP_NAME="MirrorZ-Hecras"
VERSION="$(python3 -c 'from mirrorz import __version__; print(__version__)')"
ARCH="$(uname -m)"

# If a venv was already prepared (e.g. by a test/CI step earlier), reuse it.
# Otherwise build one. We install only what's needed to freeze the app -
# no editable install of the project itself.
if [[ ! -d ".build-venv" ]]; then
    python3 -m venv .build-venv
fi
# shellcheck source=/dev/null
source .build-venv/bin/activate
# pip upgrade is a nicety, not a requirement - distros that protect their
# system pip (debian, RHEL) will reject it. Don't let that stop the build.
python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install -r requirements.txt pyinstaller pillow >/dev/null

python3 packaging/make_icons.py || echo "(icon generation skipped)"

rm -rf build "dist/${APP_NAME}"
pyinstaller --noconfirm --log-level WARN packaging/mirrorz.spec

TARBALL="dist/${APP_NAME}-${VERSION}-linux-${ARCH}.tar.gz"
tar -C dist -czf "${TARBALL}" "${APP_NAME}"
SIZE_HUMAN="$(du -h "${TARBALL}" | cut -f1)"

# Drop a copy on the Desktop if one exists - same convenience the macOS
# script provides. Linux users on a server-style box have no Desktop and
# get the tarball in dist/ as usual.
DESKTOP="${HOME}/Desktop"
if [[ -d "${DESKTOP}" ]]; then
    cp "${TARBALL}" "${DESKTOP}/"
    echo "==> DONE: ${DESKTOP}/$(basename "${TARBALL}")  (${SIZE_HUMAN})"
else
    echo "==> DONE: ${TARBALL}  (${SIZE_HUMAN})"
fi
