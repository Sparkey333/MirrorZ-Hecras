# Packaging & Distribution Guide

This is the end-to-end playbook for turning the repo into installable apps:
a **DMG on your Mac desktop**, a **Windows installer**, a **Linux tarball**,
and what it takes to list on the **Mac App Store** and **Microsoft Store**.

> **One rule before anything else: builds are not cross-platform.**
> PyInstaller freezes the Python interpreter *of the machine it runs on*.
> The DMG must be built on a Mac, the EXE on Windows. The scripts in
> `packaging/` are written so each is a one-command build on its platform.

---

## 1. Quick reference

| Target | Run on | Command | Output |
|---|---|---|---|
| macOS DMG | macOS | `bash packaging/build_macos_dmg.sh` | `~/Desktop/MirrorZ-Hecras-<ver>.dmg` |
| Windows installer | Windows | `packaging\build_windows.bat` | `dist\MirrorZ-Hecras-Setup.exe` |
| Linux tarball | Linux | `bash packaging/build_linux.sh` | `dist/MirrorZ-Hecras-<ver>-linux-x86_64.tar.gz` |
| Icons only | any | `python packaging/make_icons.py` | `assets/mirrorz_*.png`, `.ico`, `.icns` |

The version number is read from `mirrorz/__init__.py` everywhere — bump it
there and every artifact name follows.

---

## 2. macOS: DMG on your desktop

### 2.1 Dev build (no Apple account needed)

```bash
bash packaging/build_macos_dmg.sh
```

This creates the `.app`, ad-hoc signs it (required on Apple Silicon), wraps
it in a drag-to-Applications DMG, and **copies the DMG to your Desktop**
(`### TWEAK: DESKTOP_COPY ###` in the script). Recipients will see the
"unidentified developer" Gatekeeper warning — fine for personal use and
testers, not fine for customers.

### 2.2 Distribution build (signed + notarized)

You need a paid Apple Developer account ($99/yr). One-time setup:

```bash
# 1. In Xcode or developer.apple.com create a "Developer ID Application" cert.
# 2. Store notarization credentials once:
xcrun notarytool store-credentials my-notary-profile \
    --apple-id you@example.com --team-id TEAMID1234
```

Then every release is:

```bash
export CODESIGN_ID="Developer ID Application: Your Name (TEAMID1234)"
export NOTARY_PROFILE="my-notary-profile"
bash packaging/build_macos_dmg.sh
```

The script signs with the hardened runtime (`packaging/entitlements.plist`
explains the two required entitlements), notarizes, and staples the ticket.
The result opens cleanly on any Mac — this is everything required to **sell
directly** from your own website (Gumroad, Paddle, Lemon Squeezy handle
payment + license keys for you and take ~5 %).

### 2.3 Mac App Store — honest assessment

The Mac App Store **additionally requires the App Sandbox**, and sandboxing
a PyInstaller-frozen app is the hardest path in this whole document:

* You must add `com.apple.security.app-sandbox` plus file-access
  entitlements, sign with an "Apple Distribution" cert, and package as
  `.pkg` with `productbuild`.
* Frozen interpreters often violate sandbox rules in ways that surface
  only in review (temp-dir extraction, dylib loading).

**Recommended sequencing:** ship the Developer-ID DMG first (revenue now),
then do a follow-up release for the Mac App Store using
[Briefcase](https://briefcase.readthedocs.io) (BeeWare), which produces
genuinely sandbox-compatible Xcode projects from Python apps. Treat MAS as
a *distribution channel expansion*, not the launch blocker.

---

## 3. Windows

### 3.1 Installer

`packaging\build_windows.bat` freezes the app and, if
[Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed, compiles
`packaging/windows_installer.iss` into `MirrorZ-Hecras-Setup.exe`
(per-user install, desktop shortcut optional, silent-install capable).

Unsigned EXEs trigger SmartScreen "unrecognized app" warnings. Fixes, in
ascending cost:
1. Ship anyway; tell users to click "More info → Run anyway" (testers only).
2. Standard code-signing cert (~$80–200/yr) — warning fades as reputation builds.
3. **EV cert or Azure Trusted Signing (~$10/mo)** — immediate reputation.
   Azure Trusted Signing is the current best value for indie developers.

### 3.2 Microsoft Store

The Store accepts Win32 apps packaged as **MSIX** — far easier than Apple's
sandbox for our case:

1. One-time: register a Partner Center account ($19 individual).
2. Wrap the PyInstaller output with the **MSIX Packaging Tool** (free,
   Microsoft) — point it at `dist\MirrorZ-Hecras\`, fill in identity
   from Partner Center.
3. Store signing is handled by Microsoft — **no code-signing cert needed**,
   which makes the Store the *cheapest* trusted Windows channel.
4. Microsoft's cut: 15 % for apps (12 % for games as of this writing).

---

## 4. Linux

`build_linux.sh` makes a portable tarball. For store-like reach, the path
is **Flathub** (Flatpak): free to publish, no signing fees, and it is where
Linux desktop users look first. A `flatpak-builder` manifest is the natural
next artifact (### TODO ### — straightforward, ~50 lines of YAML, the frozen
build already proves the app is self-contained).

---

## 5. Pre-flight checklist for any paid release

- [ ] **Rename check** — see the trademark warning in `docs/pricing.md`
      §"Naming". Do not ship a *paid* product with "HEC-RAS"/"Hecras" in
      its name or icon.
- [ ] Version bumped in `mirrorz/__init__.py`; `CHANGELOG.md` updated.
- [ ] `python -m unittest discover tests -v` passes on the build machine.
- [ ] EULA (`docs/legal/EULA_template.md` — customized!) shown in the
      installer or first launch; the engineering-use disclaimer is **not
      optional** for hydraulics software.
- [ ] Privacy policy URL live (app stores require one even for apps that
      collect nothing — ours collects nothing, the template says so).
- [ ] App tested on a clean machine/VM with no Python installed.
- [ ] Icons present (`python packaging/make_icons.py`).

## 6. Where each store's rules live

* Apple notarization: developer.apple.com → "Notarizing macOS software"
* Mac App Store review: "App Store Review Guidelines" (esp. 2.4.5 sandbox)
* Microsoft Store: partner.microsoft.com → "MSIX packaging"
* Flathub: docs.flathub.org → "App submission"
