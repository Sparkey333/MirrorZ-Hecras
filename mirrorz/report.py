"""
mirrorz/report.py
================================================================================
Profile report generation - the deliverable a paying user hands to a
professor, a client, or their future self.

WHAT THIS PRODUCES
--------------------------------------------------------------------------------
  * build_html_report(...)  -> a single self-contained .html string with the
                               plots embedded as base64 PNGs (emailable, no
                               external files, opens offline).
  * build_pdf_report(...)   -> a multi-page .pdf assembled with matplotlib's
                               PdfPages (already a dependency - no new libs).

Both reports contain, in order:
    1. Title block + run metadata (date, units, discharge, edition branding)
    2. Water-surface profile plot
    3. Results table (every section: WSE, depth, velocity, Froude, regime)
    4. Per-section cross-section thumbnails with the computed water surface
    5. Freeboard table (only if bank stations are defined)
    6. Companion findings (the same rule-based hints shown after a run)
    7. Methodology note + the MANDATORY engineering disclaimer

WHY THIS MODULE EXISTS (commercial context)
--------------------------------------------------------------------------------
The edition table in admin.py gates "html_report" / "pdf_report" behind the
Pro and Classroom tiers. Until now those flags unlocked nothing. A polished,
brandable report is exactly the kind of "packaged convenience" people pay
for on top of a free engine (docs/pricing.md). Students turn these in;
instructors grade from them; juniors attach them to a memo.

### WARN ###: every report MUST carry the educational-use disclaimer. This
is not decorative - it is the legal posture that keeps a $30 product viable
without professional-liability exposure (docs/pricing.md §5). Do not remove
DISCLAIMER_TEXT or the footer that renders it.

HIGHLIGHTED TWEAK AREAS
--------------------------------------------------------------------------------
  ### TWEAK: REPORT_CSS ###      Look & feel of the HTML report.
  ### TWEAK: THUMB_LIMIT ###     Max cross-section thumbnails embedded.
  ### TWEAK: DISCLAIMER_TEXT ###  The legal disclaimer wording.
================================================================================
"""

from __future__ import annotations

import base64
import datetime as _dt
import html
import io
from typing import List, Optional

# matplotlib is already a dependency. We use the Figure API directly (not
# pyplot) so report rendering is thread-safe and never pops a window, even
# if called from a background job or the headless CLI.
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_pdf import PdfPages

from .geometry import CrossSection, Reach
from .solver import ProfileResult
from . import plotting as pl
from . import analyzer
from . import companion as helper
from . import __version__


# ### TWEAK: THUMB_LIMIT ###
# Cap on how many cross-section thumbnails go into a report. A 200-section
# river would otherwise produce a 50 MB HTML file. Above the cap we embed an
# evenly-spaced sample and say so. 24 keeps a typical report under ~2 MB.
THUMB_LIMIT = 24

# ### TWEAK: DISCLAIMER_TEXT ###
# Mirrors the EULA §2 language. Keep it conspicuous and unedited.
DISCLAIMER_TEXT = (
    "This report was produced by MirrorZ-Hecras, an EDUCATIONAL tool for "
    "learning open-channel hydraulics. It is NOT certified or validated for "
    "regulatory floodplain mapping, or for the design of levees, dams, "
    "bridges, culverts, or any structure whose failure could endanger life "
    "or property. Results may differ from validated software including "
    "HEC-RAS. Engineering decisions must be made by a qualified, licensed "
    "professional using validated tools."
)

METHODOLOGY_TEXT = (
    "Water-surface elevations were computed with the standard-step method, "
    "iterating the 1-D energy equation between adjacent cross-sections. "
    "Friction slope is from Manning's equation; conveyance is subdivided by "
    "left-overbank / channel / right-overbank panels where bank stations are "
    "defined. Critical depth is found by locating the minimum-specific-energy "
    "depth for the given discharge. See docs/automation.md and the inline "
    "### LEARN ### notes in mirrorz/hydraulics.py and mirrorz/solver.py."
)


# =============================================================================
# Figure -> PNG bytes -> base64 data URI
# =============================================================================

def _figure_to_png_bytes(fig: Figure, dpi: int = 130) -> bytes:
    """Render a Matplotlib Figure to PNG bytes without touching pyplot."""
    canvas = FigureCanvasAgg(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white",
                bbox_inches="tight")
    return buf.getvalue()


def _png_data_uri(fig: Figure) -> str:
    b64 = base64.b64encode(_figure_to_png_bytes(fig)).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _profile_fig(result: ProfileResult,
                 reach: Reach) -> Figure:
    fig = Figure(figsize=pl.PROFILE_FIGSIZE)
    ax = fig.add_subplot(111)
    pl.profile_figure(result, reach.cross_sections, ax=ax)
    fig.tight_layout()
    return fig


def _xs_fig(xs: CrossSection, wse: Optional[float]) -> Figure:
    fig = Figure(figsize=(4.6, 2.8))
    ax = fig.add_subplot(111)
    pl.cross_section_figure(xs, wse=wse, ax=ax)
    fig.tight_layout()
    return fig


def _sampled_sections(result: ProfileResult) -> List:
    """Return at most THUMB_LIMIT sections, evenly spaced if over the cap."""
    secs = result.sections
    if len(secs) <= THUMB_LIMIT:
        return list(secs)
    step = len(secs) / THUMB_LIMIT
    return [secs[int(i * step)] for i in range(THUMB_LIMIT)]


# =============================================================================
# HTML report
# =============================================================================

# ### TWEAK: REPORT_CSS ###
# Deliberately echoes the pitch-deck palette so the brand reads as one family.
_REPORT_CSS = """
:root{--ink:#1a2233;--muted:#5b6580;--accent:#2a72c1;--rule:#dde3ee;
      --warn:#a35a00;--err:#b3261e;--ok:#157347;--bg:#ffffff}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
     color:var(--ink);background:var(--bg);margin:0;padding:2.5rem 3rem;
     line-height:1.5;max-width:1000px;margin:0 auto}
h1{font-size:1.9rem;margin:0 0 .2rem;letter-spacing:-.02em}
h2{font-size:1.2rem;color:var(--accent);margin:2rem 0 .6rem;
   border-bottom:2px solid var(--rule);padding-bottom:.25rem}
.meta{color:var(--muted);font-size:.92rem;margin-bottom:.4rem}
.brand{font-weight:600;color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:.92rem;margin:.5rem 0}
th,td{padding:.4rem .55rem;border-bottom:1px solid var(--rule);text-align:right}
th{color:var(--accent);text-align:right;font-weight:600}
th:first-child,td:first-child{text-align:left}
tr:hover td{background:#f6f9fe}
.center{text-align:center}
img{max-width:100%;border:1px solid var(--rule);border-radius:8px}
.thumbs{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem}
.hint{padding:.4rem .7rem;border-radius:7px;margin:.3rem 0;font-size:.92rem}
.hint.info{background:#eef5ff} .hint.warn{background:#fff4e5;color:var(--warn)}
.hint.error{background:#fdecea;color:var(--err)}
.bad{color:var(--err);font-weight:600}.good{color:var(--ok)}
.disclaimer{margin-top:2.5rem;padding:1rem 1.2rem;border:1px solid #e3b9b4;
   background:#fdf3f1;border-radius:8px;color:#7a2018;font-size:.86rem}
.footer{margin-top:1.5rem;color:var(--muted);font-size:.8rem;
   border-top:1px solid var(--rule);padding-top:.7rem}
.method{font-size:.86rem;color:var(--muted)}
"""


def build_html_report(result: ProfileResult, reach: Reach,
                      project_name: str = "",
                      brand_caption: str = "",
                      title: str = "Water-Surface Profile Report") -> str:
    """
    Assemble a fully self-contained HTML report string.

    Parameters
    ----------
    brand_caption : str
        Classroom-edition branding line (institution · course · instructor).
        Pass admin.header_caption(); empty string for no branding.
    """
    esc = html.escape
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    parts: List[str] = []
    parts.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width,"
                 "initial-scale=1'>")
    parts.append(f"<title>{esc(title)}</title><style>{_REPORT_CSS}</style>")
    parts.append("</head><body>")

    # ---- Title block --------------------------------------------------
    parts.append(f"<h1>{esc(title)}</h1>")
    if brand_caption:
        parts.append(f"<div class='brand'>{esc(brand_caption)}</div>")
    if project_name:
        parts.append(f"<div class='meta'>Project: {esc(project_name)}</div>")
    parts.append(
        f"<div class='meta'>Reach: {esc(result.reach_name)} &nbsp;·&nbsp; "
        f"Discharge Q = {result.discharge:g} &nbsp;·&nbsp; "
        f"Units: {esc(result.unit_system)} &nbsp;·&nbsp; "
        f"Generated {now} &nbsp;·&nbsp; MirrorZ-Hecras v{__version__}</div>"
    )

    # ---- Profile plot -------------------------------------------------
    parts.append("<h2>Water-surface profile</h2>")
    parts.append(f"<div class='center'><img alt='profile' "
                 f"src='{_png_data_uri(_profile_fig(result, reach))}'></div>")

    # ---- Results table ------------------------------------------------
    parts.append("<h2>Results by cross-section</h2>")
    parts.append("<table><thead><tr>"
                 "<th>Section</th><th>Station</th><th>WSE</th><th>Depth</th>"
                 "<th>Velocity</th><th>Froude</th><th>Energy</th>"
                 "<th>Regime</th><th>Conv?</th></tr></thead><tbody>")
    for s in result.sections:
        conv = ("<span class='good'>yes</span>" if s.converged
                else "<span class='bad'>NO</span>")
        parts.append(
            f"<tr><td>{esc(s.name)}</td><td>{s.station:.1f}</td>"
            f"<td>{s.wse:.3f}</td><td>{s.depth:.3f}</td>"
            f"<td>{s.velocity:.3f}</td><td>{s.froude:.3f}</td>"
            f"<td>{s.energy_grade:.3f}</td><td>{esc(s.flow_regime)}</td>"
            f"<td>{conv}</td></tr>"
        )
    parts.append("</tbody></table>")

    # ---- Freeboard (only if banks defined somewhere) ------------------
    fb_rows = analyzer.freeboard_check(result, reach)
    if fb_rows:
        parts.append("<h2>Freeboard check</h2>")
        parts.append("<table><thead><tr><th>Section</th><th>WSE</th>"
                     "<th>Top of bank</th><th>Freeboard</th><th>Status</th>"
                     "</tr></thead><tbody>")
        for r in fb_rows:
            status = ("<span class='good'>OK</span>" if r.ok
                      else "<span class='bad'>LOW</span>")
            parts.append(
                f"<tr><td>{esc(r.xs_name)}</td><td>{r.wse:.3f}</td>"
                f"<td>{r.top_of_bank:.3f}</td><td>{r.freeboard:.3f}</td>"
                f"<td>{status}</td></tr>"
            )
        parts.append("</tbody></table>")

    # ---- Companion findings -------------------------------------------
    hints = helper.next_steps(result)
    if hints:
        parts.append("<h2>Companion findings</h2>")
        for h in hints:
            parts.append(f"<div class='hint {esc(h.level)}'>"
                         f"[{esc(h.level)}] {esc(h.message)}</div>")

    # ---- Cross-section thumbnails -------------------------------------
    parts.append("<h2>Cross-sections</h2>")
    sampled = _sampled_sections(result)
    if len(sampled) < len(result.sections):
        parts.append(f"<div class='meta'>Showing {len(sampled)} of "
                     f"{len(result.sections)} sections (evenly sampled).</div>")
    by_name = {xs.name: xs for xs in reach.cross_sections}
    wse_by_name = {s.name: s.wse for s in result.sections}
    parts.append("<div class='thumbs'>")
    for s in sampled:
        xs = by_name.get(s.name)
        if xs is None:
            continue
        uri = _png_data_uri(_xs_fig(xs, wse_by_name.get(s.name)))
        parts.append(f"<img alt='{esc(s.name)}' src='{uri}'>")
    parts.append("</div>")

    # ---- Methodology + disclaimer -------------------------------------
    parts.append("<h2>Methodology</h2>")
    parts.append(f"<p class='method'>{esc(METHODOLOGY_TEXT)}</p>")
    parts.append(f"<div class='disclaimer'><strong>Disclaimer.</strong> "
                 f"{esc(DISCLAIMER_TEXT)}</div>")
    parts.append("<div class='footer'>Generated by MirrorZ-Hecras "
                 f"v{__version__} · educational open-channel hydraulics</div>")
    parts.append("</body></html>")
    return "".join(parts)


def save_html_report(path: str, result: ProfileResult, reach: Reach,
                     **kwargs) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_html_report(result, reach, **kwargs))


# =============================================================================
# PDF report (matplotlib PdfPages - no extra dependency)
# =============================================================================

def build_pdf_report(path: str, result: ProfileResult, reach: Reach,
                     project_name: str = "",
                     brand_caption: str = "",
                     title: str = "Water-Surface Profile Report") -> None:
    """
    Write a multi-page PDF: page 1 = title + profile plot + results table,
    following pages = cross-section thumbnails, last page = disclaimer.

    We render the table and text directly onto Figures so the whole document
    is vector/clean and needs no HTML-to-PDF engine.
    """
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    with PdfPages(path) as pdf:
        # ---- Page 1: title + profile -------------------------------------
        fig = Figure(figsize=(8.5, 11))   # US Letter portrait
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.97)
        meta = f"{brand_caption + '   ·   ' if brand_caption else ''}" \
               f"Reach: {result.reach_name}   ·   Q = {result.discharge:g}   " \
               f"·   Units: {result.unit_system}   ·   {now}"
        fig.text(0.5, 0.93, meta, ha="center", fontsize=8, color="#555")
        if project_name:
            fig.text(0.5, 0.915, f"Project: {project_name}", ha="center",
                     fontsize=8, color="#555")
        # Profile plot occupies the top half.
        ax = fig.add_axes([0.10, 0.52, 0.82, 0.36])
        pl.profile_figure(result, reach.cross_sections, ax=ax)
        # Results table in the bottom half.
        ax_t = fig.add_axes([0.06, 0.06, 0.88, 0.40]); ax_t.axis("off")
        col_labels = ["Section", "Sta.", "WSE", "Depth", "Vel.",
                      "Fr", "Energy", "Regime", "Conv?"]
        cells = [[s.name, f"{s.station:.0f}", f"{s.wse:.2f}", f"{s.depth:.2f}",
                  f"{s.velocity:.2f}", f"{s.froude:.2f}", f"{s.energy_grade:.2f}",
                  s.flow_regime, "yes" if s.converged else "NO"]
                 for s in result.sections]
        tbl = ax_t.table(cellText=cells, colLabels=col_labels, loc="upper center")
        tbl.auto_set_font_size(False); tbl.set_fontsize(7); tbl.scale(1, 1.3)
        pdf.savefig(fig)

        # ---- Cross-section pages (4 per page) ----------------------------
        sampled = _sampled_sections(result)
        by_name = {xs.name: xs for xs in reach.cross_sections}
        wse_by_name = {s.name: s.wse for s in result.sections}
        per_page = 4
        for start in range(0, len(sampled), per_page):
            figp = Figure(figsize=(8.5, 11))
            figp.suptitle("Cross-sections", fontsize=13, y=0.97)
            chunk = sampled[start:start + per_page]
            for j, s in enumerate(chunk):
                xs = by_name.get(s.name)
                if xs is None:
                    continue
                axp = figp.add_subplot(2, 2, j + 1)
                pl.cross_section_figure(xs, wse=wse_by_name.get(s.name), ax=axp)
                axp.title.set_fontsize(8)
            figp.tight_layout(rect=[0, 0, 1, 0.95])
            pdf.savefig(figp)

        # ---- Disclaimer page --------------------------------------------
        figd = Figure(figsize=(8.5, 11)); figd.text(
            0.1, 0.9, "Methodology & Disclaimer", fontsize=14,
            fontweight="bold")
        figd.text(0.1, 0.8, METHODOLOGY_TEXT, fontsize=9, wrap=True, va="top")
        figd.text(0.1, 0.55, "Disclaimer", fontsize=11, fontweight="bold")
        figd.text(0.1, 0.50, DISCLAIMER_TEXT, fontsize=9, wrap=True, va="top",
                  color="#7a2018")
        figd.text(0.1, 0.05, f"Generated by MirrorZ-Hecras v{__version__}",
                  fontsize=8, color="#777")
        pdf.savefig(figd)

        # PDF document metadata (shows in a reader's "Properties").
        d = pdf.infodict()
        d["Title"] = title
        d["Creator"] = f"MirrorZ-Hecras v{__version__}"
        d["Subject"] = "Educational open-channel hydraulics report"
