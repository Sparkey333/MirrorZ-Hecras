# Beaver Creek (teaching distill)

`examples/beaver_creek.json` mirrors the **automation demo shape** of the
classic `BEAVCREK` example used throughout *Breaking the HEC-RAS Code*
(open project → compute → `Output_NodeOutput` at a mid-reach node).

Not a bit-exact USACE file. Swap in real XS data from your synced
`docs/reference/hec-ras-examples/` tree when available.

## Why this case

- Five naturalized sections with LOB / channel / ROB n contrast
- Good roughness-calibration and Monte Carlo target (`BC-5`)
- Discharge sweeps feel like a mini flood-frequency study

## Quick run

```bash
python main.py --run examples/beaver_creek.json
```

```python
from mirrorz.controller import Controller
rc = Controller().open_project("examples/beaver_creek.json")
for n, wse in rc.monte_carlo_manning(
        n_mean=0.032, n_std=0.004, samples=40, node="BC-5"):
    print(f"n={n:.3f}  WSE={wse:.3f}")
```
