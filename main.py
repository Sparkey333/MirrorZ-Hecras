"""
main.py - entry point for MirrorZ-Hecras.

Usage:
    python main.py                    # launch the GUI
    python main.py --cli               # launch an interactive CLI session
    python main.py --run examples/simple_channel.json
                                      # load, run, print summary, exit

NOTE
--------------------------------------------------------------------------------
Headless/server environments can import the package directly without Tk:

    from mirrorz.project import Project
    from mirrorz.solver import solve_profile
    p = Project.load("examples/simple_channel.json")
    p.apply_units()
    res = solve_profile(p.reaches[0], p.flows[0].discharge,
                        p.flows[0].boundary_wse)
    print(len(res.sections), "sections")
"""

from __future__ import annotations

import argparse
import sys


def _run_headless(path: str, report_path: str | None = None) -> int:
    from mirrorz.project import Project
    from mirrorz.solver import solve_profile
    from mirrorz.analyzer import summarize
    from mirrorz.companion import next_steps, inspect_project
    p = Project.load(path)
    p.apply_units()
    hints = inspect_project(p)
    for h in hints:
        print(f"[inspect:{h.level}] {h.message}")
    if not p.flows:
        print("No flow plan - nothing to run.")
        return 0
    flow = p.flows[0]
    result = solve_profile(p.reaches[0], flow.discharge, flow.boundary_wse,
                           regime=flow.regime)
    print(summarize(result))
    print()
    for h in next_steps(result):
        print(f"[post:{h.level}] {h.message}")

    # Optional report export. We pick HTML vs PDF from the file extension so
    # the same flag serves both: --report out.html or --report out.pdf.
    if report_path:
        from mirrorz import report as _report
        if report_path.lower().endswith(".pdf"):
            _report.build_pdf_report(report_path, result, p.reaches[0],
                                     project_name=p.name)
        else:
            _report.save_html_report(report_path, result, p.reaches[0],
                                     project_name=p.name)
        print(f"\nReport written to {report_path}")
    return 0


def _run_cli() -> int:
    """Minimal REPL for poking at a default project without a display."""
    from mirrorz.project import default_project
    from mirrorz.solver import solve_profile
    from mirrorz.analyzer import summarize
    print("MirrorZ-Hecras CLI. Type 'help' for commands.")
    p = default_project(); p.apply_units()
    while True:
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(); return 0
        if cmd in ("q", "quit", "exit"):
            return 0
        if cmd in ("h", "help", "?"):
            print("run         - compute the default flow profile")
            print("show        - print project summary")
            print("quit        - exit")
            continue
        if cmd == "show":
            print(f"Project: {p.name}  units={p.unit_system}")
            for r in p.reaches:
                print(f"  Reach {r.name}: {len(r)} XS")
            for f in p.flows:
                print(f"  Flow  {f.name}: Q={f.discharge}  WSE0={f.boundary_wse}")
            continue
        if cmd == "run":
            f = p.flows[0]
            res = solve_profile(p.reaches[0], f.discharge, f.boundary_wse,
                                regime=f.regime)
            print(summarize(res))
            continue
        print(f"unknown: {cmd!r}")


def main(argv: list[str] | None = None) -> int:
    from mirrorz import __version__
    parser = argparse.ArgumentParser(description="MirrorZ-Hecras launcher")
    parser.add_argument("--version", action="version",
                        version=f"MirrorZ-Hecras {__version__}")
    parser.add_argument("--cli", action="store_true", help="run CLI repl")
    parser.add_argument("--run", metavar="PROJECT.json",
                        help="load project, run first flow, print summary")
    parser.add_argument("--report", metavar="OUT.html|OUT.pdf",
                        help="with --run, also write a report (format from "
                             "the file extension)")
    args = parser.parse_args(argv)

    if args.run:
        return _run_headless(args.run, report_path=args.report)
    if args.cli:
        return _run_cli()

    # Default: launch GUI
    try:
        from mirrorz.gui import launch
    except Exception as e:
        print(f"GUI unavailable ({e}). Use --cli or --run for headless mode.")
        return 1
    launch()
    return 0


if __name__ == "__main__":
    sys.exit(main())
