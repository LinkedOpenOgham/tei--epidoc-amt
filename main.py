#!/usr/bin/env python3
"""Single entry point of tei--epidoc-amt.

    python main.py                 convert, diagrams, docs, tests (no network)
    python main.py --list          show the steps
    python main.py --only docs     run one step (or several: --only convert docs)
    python main.py --only check    validate with the AMT runner (needs network; never in the default run)
    python main.py --only reason   let the AMT engine reason and list what it derives (needs network; on request)

The steps are the modules py/step_*.py; each has a run() that returns 0 on success.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "py"))

STEPS = [  # (name, module, in the default run, what it does)
    ("convert",  "step_convert",  True,  "EpiDoc -> out/*.amt.ttl and out/README.md"),
    ("diagrams", "step_diagrams", True,  "six figures into docs/diagrams/"),
    ("docs",     "step_docs",     True,  "GitHub Pages documentation into docs/"),
    ("tests",    "step_tests",    True,  "unit tests of the converter"),
    ("check",    "step_check",    False, "AMT runner --check-only on every graph (network)"),
    ("reason",   "step_reason",   False, "AMT engine reasoning on every graph, report of derived edges (network)"),
]


def call(module: str) -> int:
    mod = __import__(module)
    if module == "step_convert":
        return mod.main([])
    return mod.run() if hasattr(mod, "run") else mod.main()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="show the steps and exit")
    ap.add_argument("--only", nargs="+", metavar="STEP", help="run only these steps")
    args = ap.parse_args()
    names = [s[0] for s in STEPS]
    if args.list:
        for name, _, default, text in STEPS:
            print(f"  {name:9} {'default' if default else 'on request'}  {text}")
        return 0
    chosen = args.only or [s[0] for s in STEPS if s[2]]
    unknown = [c for c in chosen if c not in names]
    if unknown:
        ap.error(f"unknown step(s): {', '.join(unknown)}; choose from {', '.join(names)}")
    for name, module, _, _ in STEPS:
        if name in chosen:
            print(f"\n=== step: {name} ===")
            code = call(module)
            if code:
                print(f"step {name} failed with exit code {code}", file=sys.stderr)
                return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
