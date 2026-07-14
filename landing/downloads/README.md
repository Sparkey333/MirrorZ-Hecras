# macOS downloads

This folder is where `packaging/build_macos_dmg.sh` drops:

```
MirrorZ-Hecras-<version>.dmg
MirrorZ-Hecras-<version>.dmg.sha256
```

The landing page (`../index.html`) links to `MirrorZ-Hecras-0.5.1.dmg`.

## Why the DMG is missing in cloud agents

PyInstaller / `hdiutil` **cannot** produce a runnable Mac app on Linux.
Build on a Mac (or via the GitHub Actions `macos-dmg` workflow):

```bash
bash packaging/build_macos_dmg.sh
# → ~/Downloads/MirrorZ-Hecras-0.4.0.dmg
# → landing/downloads/MirrorZ-Hecras-0.4.0.dmg
```

Large `.dmg` binaries are gitignored; ship them via GitHub Releases or your host.
