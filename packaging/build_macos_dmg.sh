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

cd "$(dirname "$0")/.."     # repo root, regardless of where invoked from

APP_NAME="MirrorZ-Hecras"
VERSION="$(python3 -c 'from mirrorz import __version__; print(__version__)')"
DIST="dist"
APP_PATH="${DIST}/${APP_NAME}.app"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
DMG_PATH="${DIST}/${DMG_NAME}"

echo "==> Building ${APP_NAME} ${VERSION} for macOS"

# ----------------------------------------------------------------------------
# 1. Fresh virtualenv keeps the bundle free of stray site-packages.
# ----------------------------------------------------------------------------
python3 -m venv .build-venv
source .build-venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e ".[package]" >/dev/null

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
# 7. ### TWEAK: DESKTOP_COPY ### - drop the finished DMG on the Desktop.
# ----------------------------------------------------------------------------
DESKTOP="${HOME}/Desktop"
if [[ -d "${DESKTOP}" ]]; then
    cp "${DMG_PATH}" "${DESKTOP}/"
    echo "==> DONE: ${DESKTOP}/${DMG_NAME}"
else
    echo "==> DONE: ${DMG_PATH}"
fi
