# MirrorZ-Hecras

An educational, open-source **mirror** of [HEC-RAS](https://www.hec.usace.army.mil/software/hec-ras/)
— the U.S. Army Corps of Engineers' river analysis tool. This project re-implements
the core ideas of 1-D steady-flow open-channel hydraulics in pure, heavily-commented
Python so you can *read every step* of the math that HEC-RAS hides behind its GUI.

> **Not** a drop-in replacement for HEC-RAS. Not certified for regulatory floodplain
> work. Built for learning, classroom use, and quick sensitivity experiments.

---

## What it does

- **1-D steady-flow water-surface profiles** using the standard-step method
  (sub- and super-critical regimes)
- **Cross-section geometry** with irregular ground points and LOB / channel / ROB
  panels (different Manning's n per region)
- **Critical depth & normal depth** solvers on arbitrary sections
- **Companion wizard** — rule-based guidance, glossary, sanity checks
- **Analyzer** — rating curves, freeboard checks, CSV-style summaries
- **Tk GUI** with embedded matplotlib plots
- **JSON project files** that are human-readable and diff-friendly

## Quick start

```bash
pip install -r requirements.txt

# Launch the GUI
python main.py

# Or run a sample project headless (prints a summary table)
python main.py --run examples/simple_channel.json

# Or a minimal CLI REPL for environments without a display
python main.py --cli
```

## Project layout

```
MirrorZ-Hecras/
├── main.py              entry point (GUI / CLI / headless)
├── requirements.txt
├── src/
│   ├── hydraulics.py    Manning, Froude, critical & normal depth, conveyance
│   ├── geometry.py      CrossSection, Reach; wetted-area math
│   ├── solver.py        Standard-step water-surface profile solver
│   ├── project.py       JSON I/O + default project factory
│   ├── companion.py     "Hecras Helper" — explanations + sanity checks
│   ├── analyzer.py      rating curve, freeboard, summary
│   ├── plotting.py      matplotlib cross-section & profile figures
│   └── gui.py           Tkinter desktop application
├── examples/
│   ├── simple_channel.json
│   └── natural_river.json
└── tests/
    └── test_smoke.py
```

## Reading the code (you said you're using this to learn!)

Every source file opens with a banner explaining the file's purpose and lists
the **search tags** used throughout. Grep for any of these to jump to the spots
most worth understanding or tweaking:

| Tag | What it marks |
|---|---|
| `### TWEAK ###` | Knobs you are likely to change (constants, defaults, tolerances) |
| `### LEARN ###` | Short teaching blocks about hydraulics or numerics |
| `### WARN ###`  | Common pitfalls and failure modes |
| `### TODO ###`  | Extension points left open on purpose |

For example, to quickly find every "magic number" in the code:

```bash
grep -n "### TWEAK" src/*.py
```

Highlighted tweak categories already in place:

- `### TWEAK: UNITS ###` – SI vs. US customary
- `### TWEAK: NUMERIC_TOLS ###` – solver tolerances and iteration caps
- `### TWEAK: ROOT_FINDER ###` – scipy vs. pure-Python bisection
- `### TWEAK: DEFAULT_N ###` – Manning's n default
- `### TWEAK: FRICTION_AVG ###` – which averaging scheme for S_f
- `### TWEAK: SOLVER_TOL ###` – energy convergence tolerance
- `### TWEAK: DEFAULT_PROJECT ###` – the shape of the auto-generated sample
- `### TWEAK: SANITY_LIMITS ###` – thresholds the companion uses to warn you
- `### TWEAK: STYLE ###` / `### TWEAK: FIG_SIZE ###` – plot look and feel

## How the math lines up with HEC-RAS

| Concept | HEC-RAS reference manual | File here |
|---|---|---|
| Manning's equation | §2-1 | `src/hydraulics.py` → `manning_discharge`, `friction_slope` |
| Conveyance subdivision | §2-2 | `src/geometry.py` → `CrossSection.panels` |
| Standard-step energy eq. | §2-2 | `src/solver.py` → `_step_between` |
| Critical depth | §2-3 | `src/hydraulics.py` → `critical_depth` |
| Contraction / expansion losses | §2-4 | `src/solver.py` → `_step_between` |

## What it does NOT do (yet)

These are real, necessary features of HEC-RAS that are intentionally out of
scope for a teaching mirror — each is a great learning extension:

- Unsteady 1-D flow (the HEC-RAS Saint-Venant solver)
- Mixed-regime profiles (hydraulic jumps)
- Bridges, culverts, weirs, gates
- Ineffective flow areas and levees
- 2-D mesh flow (RAS Mapper)
- Sediment transport
- Water-quality modules

See `### TODO ###` markers throughout the code for small extension hooks.

## Running the tests

```bash
python -m unittest tests.test_smoke -v
```

The smoke tests validate Manning round-trip, check the generic critical /
normal-depth solvers against closed-form rectangular formulas, and make sure
both example projects run end-to-end.

## License & credits

- **HEC-RAS** is a public-domain U.S. Government work developed by the
  Hydrologic Engineering Center of the U.S. Army Corps of Engineers. This
  project only mirrors *concepts*; no HEC-RAS source is incorporated.
- **Roughness values** referenced: Chow, V.T. (1959), *Open-Channel Hydraulics*.
- Distributed under the MIT License (see `LICENSE`).
