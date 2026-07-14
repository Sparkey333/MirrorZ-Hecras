# Critical Creek (teaching distill)

`examples/critical_creek.json` is a **teaching distillation** of the pattern
made famous by HEC-RAS Applications Guide Chapter 1 ("Critical Creek") and
by Goodell / RAS Solution automation demos.

It is **not** a bit-exact copy of USACE geometry. When you sync real Example
Data into `docs/reference/hec-ras-examples/`, replace stations/elevations
here and tighten the regression tolerances in `tests/test_examples.py`.

## Why this case

- Short mild-slope trapezoidal reach (four XS)
- Single steady discharge, known downstream WSE
- Ideal first automation target: open → compute → read node 3

## Quick run

```bash
python main.py --run examples/critical_creek.json
```

```python
from mirrorz.controller import Controller
rc = Controller().open_project("examples/critical_creek.json")
rc.compute_current_plan()
print(rc.output("CC-160", "wse"))
```
