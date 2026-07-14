# Automation Guide — scripting MirrorZ like *Breaking the HEC-RAS Code*

Chris Goodell's book *Breaking the HEC-RAS Code: A User's Guide to
Automating HEC-RAS* (h2ls, 2014) is the standard reference for driving
HEC-RAS from code via its Windows COM object, `HECRASController`. Its core
workflow is:

```
open project → pick plan → compute → read outputs by node → repeat at scale
```

MirrorZ ships the same workflow natively in `mirrorz/controller.py` — no
COM, no Windows requirement, no `QuitRAS()` cleanup, because the engine is
in-process Python.

> Note on the book itself: it is a copyrighted commercial work, so the text
> is **not** included in this repository (don't commit your PDF copy to a
> public repo either). What lives here is an original implementation of the
> publicly documented API *workflow* the book teaches. If you want specific
> chapters reflected in code, drop notes/excerpts into a local
> `docs/reference/` folder (gitignored) and open an issue describing the
> recipe to add.

## API correspondence

| HECRASController (book) | MirrorZ `Controller` |
|---|---|
| `Project_Open(path)` | `open_project(path)` |
| `Project_Save()` | `save_project(path)` |
| `Plan_Names()` | `plan_names()` |
| `Plan_SetCurrent(name)` | `set_current_plan(name)` |
| `Compute_CurrentPlan()` | `compute_current_plan()` |
| `Geometry_GetNodes(...)` | `node_names()` |
| `Output_NodeOutput(riv, rch, node, …, varID)` | `output(node, "wse")` — keywords, not integer IDs |
| *(loop over runs in VBA)* | `compute_sweep([q1, q2, …])` |

## The book's classic recipes, in MirrorZ form

### Recipe 1 — single run, read one value

```python
from mirrorz.controller import Controller

rc = Controller().open_project("examples/simple_channel.json")
rc.compute_current_plan()
print("WSE at XS-3:", rc.output("XS-3", "wse"))
print("velocity   :", rc.output("XS-3", "velocity"))
```

### Recipe 2 — roughness calibration sweep

The most common automation task in practice: vary Manning's n until the
computed water surface matches a measured high-water mark.

```python
rc = Controller().open_project("examples/simple_channel.json")
observed_wse = 1.62          # surveyed high-water mark at XS-5

for n in (0.025, 0.030, 0.035, 0.040, 0.045):
    rc.set_manning_n(n)      # every section's channel n
    rc.compute_current_plan()
    err = rc.output("XS-5", "wse") - observed_wse
    print(f"n={n:.3f}  error={err:+.3f}")
```

### Recipe 3 — discharge sweep (mini flood-frequency study)

```python
rc = Controller().open_project("examples/natural_river.json")
for q, res in zip((20, 40, 80, 160),
                  rc.compute_sweep([20, 40, 80, 160])):
    top = max(s.wse for s in res.sections)
    print(f"Q={q:>4} cms  max WSE={top:.2f}  "
          f"converged={all(s.converged for s in res.sections)}")
```

### Recipe 4 — whole-profile table for a report

```python
rc.compute_current_plan()
for node, v in rc.output_table("froude").items():
    print(f"{node:10s} Fr={v:.2f}")
```

### Recipe 5 — generate a deliverable report (HTML or PDF)

```python
rc = Controller().open_project("examples/natural_river.json")
rc.compute_current_plan()
rc.export_html_report("flood_study.html",
                      brand_caption="U of Example · CIVE 462")
rc.export_pdf_report("flood_study.pdf")
```

The same thing from the command line, format chosen by extension:

```bash
python main.py --run examples/natural_river.json --report flood_study.html
python main.py --run examples/natural_river.json --report flood_study.pdf
```

Reports are **never gated at the library/CLI layer** — the MIT engine stays
fully capable for scripting and CI. Edition gating (Pro/Classroom) applies
only to the GUI menu items, which is a storefront decision, not an engine
limitation. See `mirrorz/report.py`.

## Phase 3 additions (v0.5)

### Boundary sweeps

```python
rc = Controller().open_project("examples/critical_creek.json")
for wse in (1.2, 1.35, 1.5):
    rc.set_boundary(wse=wse)
    rc.compute_current_plan()
    print(wse, rc.output("CC-160", "wse"))
```

### Geometry what-ifs

```python
rc = Controller().open_project("examples/beaver_creek.json")
rc.raise_bed(0.15)          # aggrade every XS
rc.widen_channel(1.2)       # widen about section midpoints
rc.compute_current_plan()
```

### CSV / JSON export

```python
rc.compute_current_plan()
rc.export_results_csv("profile.csv")
rc.export_results_json("profile.json")
```

### Monte Carlo Manning's n (RAS Solution recipe)

```python
pairs = rc.monte_carlo_manning(
    n_mean=0.032, n_std=0.004, samples=50, node="BC-5")
ws = [w for _, w in pairs]
print(min(ws), sum(ws)/len(ws), max(ws))
```

## Still open

* Mixed-flow / bridge geometry (out of 1D-steady teaching scope for now)
* Optional Windows COM comparison backend (Phase 5)
