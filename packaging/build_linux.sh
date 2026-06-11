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

python3 -m venv .build-venv
source .build-venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e ".[package]" >/dev/null

python3 packaging/make_icons.py || echo "(icon generation skipped)"

rm -rf build "dist/${APP_NAME}"
pyinstaller --noconfirm packaging/mirrorz.spec

TARBALL="dist/${APP_NAME}-${VERSION}-linux-${ARCH}.tar.gz"
tar -C dist -czf "${TARBALL}" "${APP_NAME}"
echo "==> DONE: ${TARBALL}"
