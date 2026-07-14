"""
mirrorz/resources.py
================================================================================
Single source of truth for Getting-Started steps and key external URLs.

Used by:
  * companion.welcome() / companion.getting_started_text()
  * GUI Help menu (opens sites in the system browser)
  * landing/index.html (keep in sync — see docs/GETTING_STARTED.md)

### TWEAK: LINKS ###  Update URLs here first, then refresh the landing page.
================================================================================
"""

from __future__ import annotations

from typing import List, Tuple

# (label, url) — open with webbrowser.open in the GUI
KEY_SITES: List[Tuple[str, str]] = [
    ("MirrorZ GitHub (this project)",
     "https://github.com/Sparkey333/MirrorZ-Hecras"),
    ("Pull request #2 (engine + landing + v0.5)",
     "https://github.com/Sparkey333/MirrorZ-Hecras/pull/2"),
    ("HEC-RAS home (USACE download & docs)",
     "https://www.hec.usace.army.mil/software/hec-ras/"),
    ("HEC-RAS 2025 (next-gen alpha)",
     "https://www.hec.usace.army.mil/software/hec-ras/2025/"),
    ("HEC-RAS documentation library",
     "https://www.hec.usace.army.mil/software/hec-ras/documentation.aspx"),
    ("Breaking the HEC-RAS Code (Goodell / The RAS Solution)",
     "https://therassolution.kleinschmidtgroup.com/"),
    ("Automating HEC-RAS intro post",
     "http://hecrasmodel.blogspot.com/2014/10/automating-hec-ras.html"),
    ("Higgsfield AI (hero / video assets)",
     "https://higgsfield.ai/"),
    ("Higgsfield AI video studio",
     "https://higgsfield.ai/ai-video"),
    ("CivilGEO GeoHECRAS (commercial alternative)",
     "https://www.civilgeo.com/"),
]

# Numbered local-Mac workflow (always stage DMG to ~/Downloads for now)
LOCAL_MAC_STEPS: List[str] = [
    "Clone or pull the repo on this Mac: "
    "git clone https://github.com/Sparkey333/MirrorZ-Hecras.git "
    "(or git pull on your existing checkout).",
    "Optional — sync private Downloads materials into gitignored reference: "
    "./scripts/sync_local_reference.sh "
    "\"/Users/ansom/Downloads/HECRAS-Breaking Hecras Code\"",
    "Install / refresh the Python env: bash scripts/install_dev.sh && "
    "source .venv/bin/activate && pytest -q",
    "Build the Mac app + DMG (always lands in ~/Downloads and opens): "
    "bash packaging/build_macos_dmg.sh",
    "In Finder, open ~/Downloads/MirrorZ-Hecras-<version>.dmg → drag "
    "MirrorZ-Hecras.app into Applications (or run from the volume).",
    "First launch if Gatekeeper warns: right-click the app → Open → Open.",
    "Open the landing page locally: open landing/index.html "
    "(or bash packaging/open_landing.sh) — Download button points at the DMG.",
    "In the app: File → Open examples/beaver_creek.json → Run → Compute Profile.",
]


def getting_started_text() -> str:
    """Plain-text Getting Started for dialogs / Companion."""
    lines = [
        "MirrorZ-Hecras — Getting Started (local Mac)",
        "",
        "Clear steps (DMG always goes to ~/Downloads for now):",
        "",
    ]
    for i, step in enumerate(LOCAL_MAC_STEPS, 1):
        lines.append(f"  {i}. {step}")
        lines.append("")
    lines.append("Key sites:")
    lines.append("")
    for label, url in KEY_SITES:
        lines.append(f"  • {label}")
        lines.append(f"    {url}")
        lines.append("")
    lines.append(
        "Educational tool only — not certified for regulatory floodplain work. "
        "Use official HEC-RAS for permit / life-safety deliverables."
    )
    return "\n".join(lines)


def links_markdown_rows() -> str:
    """Markdown table rows for docs."""
    return "\n".join(f"| {label} | {url} |" for label, url in KEY_SITES)
