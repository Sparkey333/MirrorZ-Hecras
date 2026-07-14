"""
packaging/make_icons.py
================================================================================
Generate the application icon set from code - no design tools required.

WHAT IT DRAWS
--------------------------------------------------------------------------------
A stylized river cross-section: brown trapezoidal banks, blue water with a
dashed water-surface line. Drawn with matplotlib (already a dependency) so
the icon is reproducible and versioned with the code instead of living as
an opaque binary blob.

OUTPUTS (in assets/)
--------------------------------------------------------------------------------
    mirrorz_16..1024.png   the raw size ladder
    mirrorz.ico            Windows multi-size icon   (needs Pillow)
    mirrorz.icns           macOS icon                (needs macOS iconutil)

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: ICON_ART ###   The geometry/colors of the drawing.
================================================================================
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")               # never needs a display
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
ASSETS = os.path.join(ROOT, "assets")

# The size ladder app stores expect. 1024 is the App Store marketing size.
SIZES = (16, 32, 64, 128, 256, 512, 1024)


def draw_icon(px: int, path: str) -> None:
    """Render one square PNG of the river logo at `px` pixels."""
    # ### TWEAK: ICON_ART ###
    ground = "#7a5230"
    water = "#2a72c1"
    sky = "#eaf3fb"

    dpi = 100
    fig = plt.figure(figsize=(px / dpi, px / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])     # fill the whole canvas, no margins
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 10, 10, color=sky))

    # Trapezoidal channel: bank tops at y=7, bed at y=2.
    xs = [0, 2.5, 3.5, 6.5, 7.5, 10]
    zs = [7.5, 7, 2, 2, 7, 7.5]
    ax.fill_between(xs, zs, 0, color=ground)

    # Water up to y=5.5 inside the channel only.
    wse = 5.5
    water_xs = [3.0, 3.5, 6.5, 7.0]
    water_zs = [wse, 2, 2, wse]
    ax.fill_between(water_xs, water_zs, wse, color=water)
    # Dashed water-surface line - the signature HEC-RAS visual.
    lw = max(px / 64, 1.0)              # scale line width with icon size
    ax.plot([2.8, 7.2], [wse, wse], "--", color="white", linewidth=lw)

    fig.savefig(path, transparent=False)
    plt.close(fig)


def main() -> int:
    os.makedirs(ASSETS, exist_ok=True)
    pngs = {}
    for px in SIZES:
        path = os.path.join(ASSETS, f"mirrorz_{px}.png")
        draw_icon(px, path)
        pngs[px] = path
    print(f"PNG ladder written to {ASSETS}")

    # ---- Windows .ico (multi-resolution in one file) -----------------------
    try:
        from PIL import Image
        img = Image.open(pngs[1024])
        img.save(os.path.join(ASSETS, "mirrorz.ico"),
                 sizes=[(s, s) for s in SIZES if s <= 256])
        print("mirrorz.ico written")
    except ImportError:
        print("Pillow not installed - skipped .ico (pip install pillow)")

    # ---- macOS .icns via iconutil (only exists on macOS) -------------------
    if sys.platform == "darwin" and shutil.which("iconutil"):
        iconset = os.path.join(ASSETS, "mirrorz.iconset")
        os.makedirs(iconset, exist_ok=True)
        # Apple's iconset naming: icon_<size>x<size>[@2x].png
        for px in (16, 32, 128, 256, 512):
            shutil.copy(pngs[px], os.path.join(iconset, f"icon_{px}x{px}.png"))
            shutil.copy(pngs[px * 2],
                        os.path.join(iconset, f"icon_{px}x{px}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", iconset,
                        "-o", os.path.join(ASSETS, "mirrorz.icns")],
                       check=True)
        shutil.rmtree(iconset)
        print("mirrorz.icns written")
    elif sys.platform == "darwin":
        print("iconutil missing - skipped .icns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
