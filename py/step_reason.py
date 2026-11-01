#!/usr/bin/env python3
"""Step "reason" (network): let the AMT engine reason over the graphs and report what it derives.

Needs git and network access, so it is not part of the default build:

    python main.py --only reason

Reuses the amt-runner clone in build/ (cloned by the step "check" if it is not there) and calls, for each graph of
``out/``, ``run_amt.py <graph> --no-info --outdir build/reasoned/<base>`` (the runner adds a timestamped ``run-...`` folder). The engine validates the graph, checks the
integrity axioms (disjointness), applies the subsumptions and role chains of ``ontology/ogham-amt.ttl`` and writes
the reasoned Turtle, the CSV and Cypher exports and a Markdown report. Nothing is written outside build/.
The summary is build/reason-report.txt: per graph, the inferred edges.
"""
from __future__ import annotations

import csv
import shutil
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
    lines, failed = [], 0
    for _, base in STONES:
        target = BUILD / "reasoned" / base      # the runner adds a timestamped run-... folder below this
        if target.exists():
            shutil.rmtree(target)
        cmd = [sys.executable, str(runner / "run_amt.py"), str(OUT / f"{base}.amt.ttl"), "--no-info",
               "--outdir", str(target), "--update"]
        print(f"\n== {base}")
        p = subprocess.run(cmd, capture_output=True, text=True)
        print(p.stdout + p.stderr)
        failed += p.returncode != 0
        lines.append(f"== {base}  exit {p.returncode}")
        edges = next(target.glob("run-*/*.edges.csv"), None) if target.exists() else None
        if edges:
            with edges.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if row["inferred"] == "true":
                        lines.append("  {} -{}-> {}  {}".format(row["source_iri"].rsplit("/", 1)[-1],
                                     row["role_iri"].rsplit("/", 1)[-1], row["target_iri"].rsplit("/", 1)[-1],
                                     row["weight"]))
    write_text(BUILD / "reason-report.txt", "\n".join(lines))
    print(f"\nreport: {rel(BUILD / 'reason-report.txt')}   graphs that failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
