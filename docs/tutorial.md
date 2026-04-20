# Tutorial — your first water-surface profile

This walks through the simplest HEC-RAS-style workflow using MirrorZ-Hecras.

## 1. Launch

```bash
python main.py
```

The GUI opens on the **Companion** tab with a welcome message and next-step
tips. A default trapezoidal stream is already loaded (five cross-sections,
mild 0.1% slope, Q = 20 m³/s).

## 2. Inspect a cross-section

Click **Main Reach → XS-3** in the left tree. The **Cross-Section** tab shows
the station/elevation table and a matplotlib plot of the ground, the banks
(dotted vertical lines), and, after you run, the water surface.

Try editing a ground elevation: select a row, click *Edit Pt*, change the
number, and press *Refresh*. The plot updates live.

## 3. Run the steady profile

Click **Run → Compute Profile** (or switch to the **Profile** tab and press
*Run*). The water surface, thalweg, energy grade line, and critical WSE are
plotted along the reach. The **Summary** tab shows a CSV-style table plus any
companion warnings.

## 4. Try a higher discharge

Left panel → *Add Flow*. Give it a name (e.g. "100-yr"), a discharge, and a
regime. The companion picks a reasonable boundary WSE (normal depth at the
downstream section). Run it again and compare the two plots.

## 5. Check freeboard

With a computed profile in hand, click **Run → Freeboard Check**. The tool
compares each WSE to the lower bank-top elevation and flags sections with
less than the required freeboard (default 0.5 m, `### TWEAK: FREEBOARD_REQ ###`
in `src/analyzer.py`).

## 6. Build a rating curve

**Run → Rating Curve…** sweeps Q from your min to your max, re-running the
solver and plotting Q vs. WSE at the downstream section.

## 7. Save and version-control your project

**File → Save As…** writes a JSON file. Because the format is plain text,
you can `git diff` it to see exactly what changed between runs.

---

## Where the teaching comments live

Every source file opens with a list of `### TWEAK ###` and `### LEARN ###`
anchors. Search for them to jump to the most useful spots:

```bash
grep -n "### LEARN" src/*.py
grep -n "### TWEAK" src/*.py
```

Recommended reading order if you want the big picture:

1. `src/hydraulics.py` — the math
2. `src/geometry.py` — how shapes become hydraulic properties
3. `src/solver.py` — how the profile is marched section by section
4. `src/companion.py` — the knowledge base behind the helper
