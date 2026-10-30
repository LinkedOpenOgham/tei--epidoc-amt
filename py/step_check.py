#!/usr/bin/env python3
"""Step "check" (network): validate the graphs with the AMT runner and the AMT engine.

Needs git and network access, so it is not part of the default build:

    python main.py --only check

Clones the amt-runner into build/ (ignored by git) and calls, for each graph,
``run_amt.py <graph> --check-only --update``. The runner fetches the newest
AMT.engine (0.5.0 or newer is needed for --check-only), validates the graph
against the AMT shapes, loads it and runs the diagnostics. Nothing is written
outside build/. The report is build/check-report.txt.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ogham_amt_utils import BUILD, OUT, STONES, rel, write_text  # noqa: E402

RUNNER_URL = "https://github.com/alpaca-fair-framework/amt-runner.git"


def run() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    runner = BUILD / "amt-runner"
    if not runner.exists():
        print(f"cloning {RUNNER_URL} into {rel(runner)}")
        if subprocess.run(["git", "clone", "--depth", "1", RUNNER_URL, str(runner)]).returncode != 0:
            print("FAIL  could not clone the amt-runner (network?)", file=sys.stderr)
            return 2
    report, failed = [], 0
    for _, base in STONES:
        ttl = OUT / f"{base}.amt.ttl"
        cmd = [sys.executable, str(runner / "run_amt.py"), str(ttl), "--check-only", "--update"]
        print(f"\n== {base}")
        p = subprocess.run(cmd, capture_output=True, text=True)
        print(p.stdout + p.stderr)
        report.append(f"== {base}  exit {p.returncode}\n{p.stdout}{p.stderr}")
        failed += p.returncode != 0
    write_text(BUILD / "check-report.txt", "\n".join(report))
    print(f"\nreport: {rel(BUILD / 'check-report.txt')}   graphs with findings: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
