#!/usr/bin/env bash
# ============================================================================
# packaging/build_macos_dmg.sh - build, sign, notarize, and package the
# macOS app as a DMG, then drop a copy on your Desktop.
# ============================================================================
# RUN THIS ON A MAC. PyInstaller cannot cross-compile: a macOS app must be
# built on macOS (likewise Windows on Windows). From the repo root:
#
#     bash packaging/build_macos_dmg.sh
#
# Unsigned/dev build: works out of the box, Gatekeeper will warn users.
# Signed + notarized build (required to distribute outside the App Store):
#
#     export CODESIGN_ID="Developer ID Application: Your Name (TEAMID1234)"
#     export NOTARY_PROFILE="my-notary-profile"   # from `xcrun notarytool store-credentials`
#     bash packaging/build_macos_dmg.sh
#
# HIGHLIGHTED TWEAK AREAS
#   ### TWEAK: DESKTOP_COPY ###  where the final DMG lands
#   ### TWEAK: DMG_LOOK ###      volume name / layout of the DMG window
# ============================================================================
set -euo pipefail

# ----------------------------------------------------------------------------
# 0. Pre-flight: refuse to run anywhere we know we'll fail. This script
#    uses hdiutil and codesign (macOS-only). Catching it here gives a clear
#    error instead of a confusing one halfway through PyInstaller.
# ----------------------------------------------------------------------------
if [[ "$(uname)" != "Darwin" ]]; then
    echo "ERROR: This script must be run on macOS (hdiutil + codesign are"
    echo "       macOS-only). For Linux, run packaging/build_linux.sh"
    echo "       For Windows, run packaging\\build_windows.bat on Windows."
    exit 2
fi
for tool in hdiutil codesign python3; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: missing required tool: $tool"; exit 2; }
done

cd "$(dirname "$0")/.."     # repo root, regardless of where invoked from

APP_NAME="MirrorZ-Hecras"
VERSION="$(python3 -c 'from mirrorz import __version__; print(__version__)')"
DIST="dist"
APP_PATH="${DIST}/${APP_NAME}.app"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
DMG_PATH="${DIST}/${DMG_NAME}"

echo "==> Building ${APP_NAME} ${VERSION} for macOS ($(uname -m))"

# ----------------------------------------------------------------------------
# 1. Build-time virtualenv. We install ONLY the build tools (PyInstaller +
#    Pillow) plus the runtime deps from requirements.txt - no editable
#    install of the project itself, which keeps stray .egg-info / build
#    artifacts out of the frozen app.
# ----------------------------------------------------------------------------
python3 -m venv .build-venv
# shellcheck source=/dev/null
source .build-venv/bin/activate
# pip upgrade is a nicety; tolerate the system-pip-protected case quietly.
python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install -r requirements.txt pyinstaller pillow >/dev/null

# ----------------------------------------------------------------------------
# 2. Icons (no-op if already generated).
# ----------------------------------------------------------------------------
python3 packaging/make_icons.py || echo "(icon generation skipped)"

# ----------------------------------------------------------------------------
# 3. Freeze with PyInstaller.
# ----------------------------------------------------------------------------
rm -rf build "${DIST}/${APP_NAME}" "${APP_PATH}" "${DMG_PATH}"
pyinstaller --noconfirm packaging/mirrorz.spec
test -d "${APP_PATH}" || { echo "ERROR: .app not produced"; exit 1; }

# ----------------------------------------------------------------------------
# 4. Code-sign (hardened runtime is REQUIRED for notarization).
#    Without CODESIGN_ID we ad-hoc sign ("-") so the app at least runs
#    locally on Apple Silicon, which refuses entirely-unsigned binaries.
# ----------------------------------------------------------------------------
SIGN_ID="${CODESIGN_ID:--}"
echo "==> Signing with identity: ${SIGN_ID}"
codesign --force --deep --options runtime \
    --entitlements packaging/entitlements.plist \
    --sign "${SIGN_ID}" "${APP_PATH}"
codesign --verify --deep --strict "${APP_PATH}"

# ----------------------------------------------------------------------------
# 5. Build the DMG: a compressed disk image with the app and an
#    /Applications symlink so users drag-install the familiar way.
# ----------------------------------------------------------------------------
# ### TWEAK: DMG_LOOK ###
VOLUME_NAME="${APP_NAME} ${VERSION}"
STAGING="$(mktemp -d)"
cp -R "${APP_PATH}" "${STAGING}/"
ln -s /Applications "${STAGING}/Applications"
hdiutil create -volname "${VOLUME_NAME}" -srcfolder "${STAGING}" \
    -ov -format UDZO "${DMG_PATH}"
rm -rf "${STAGING}"

# ----------------------------------------------------------------------------
# 6. Notarize + staple (skipped unless NOTARY_PROFILE is set).
#    Notarization = Apple malware-scans the DMG and issues a ticket;
#    stapling attaches the ticket so offline Macs can verify it.
# ----------------------------------------------------------------------------
if [[ -n "${NOTARY_PROFILE:-}" ]]; then
    echo "==> Notarizing (this can take a few minutes)..."
    xcrun notarytool submit "${DMG_PATH}" \
        --keychain-profile "${NOTARY_PROFILE}" --wait
    xcrun stapler staple "${DMG_PATH}"
else
    echo "==> NOTARY_PROFILE not set - skipping notarization (dev build)."
fi

# ----------------------------------------------------------------------------
# 7. ### TWEAK: DESKTOP_COPY ### - drop the finished DMG on the Desktop and
#    report its size, plus what to do next.
# ----------------------------------------------------------------------------
DESKTOP="${HOME}/Desktop"
if [[ -d "${DESKTOP}" ]]; then
    cp "${DMG_PATH}" "${DESKTOP}/"
    FINAL="${DESKTOP}/${DMG_NAME}"
else
    FINAL="${DMG_PATH}"
fi
SIZE_HUMAN="$(du -h "${FINAL}" | cut -f1)"

echo ""
echo "==> DONE: ${FINAL}  (${SIZE_HUMAN})"
if [[ "${SIGN_ID}" == "-" ]]; then
    echo ""
    echo "    NOTE: this is an AD-HOC SIGNED build (no Developer ID)."
    echo "    First-launch on someone else's Mac will need:"
    echo "      right-click the app -> Open -> confirm in the dialog."
    echo "    For distribution, set CODESIGN_ID + NOTARY_PROFILE and"
    echo "    re-run this script."
fi
