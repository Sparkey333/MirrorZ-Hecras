# Sample outputs

Artifacts you can show on a landing page or attach to a "what you get" email.

- **`sample_report.pdf`** — a multi-page PDF report generated from
  `examples/natural_river.json` (the `Wiggle Creek` reach at Q = 80). This is
  exactly what the **Export PDF Report** menu item (Pro / Classroom edition)
  produces.

Regenerate (and make an HTML version too) any time:

```bash
python main.py --run examples/natural_river.json --report docs/samples/sample_report.pdf
python main.py --run examples/natural_river.json --report docs/samples/sample_report.html
```

The HTML version embeds all plots as base64, so it's a single self-contained
file — but it's ~400 KB, so we keep only the small PDF under version control.
