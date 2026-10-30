#!/usr/bin/env python3
"""Compatibility entry point.

``python py/main.py`` still converts the stones, with the same arguments as
before (``--input``, ``--output``, ``--shapes``, ``--ontology``). The converter
itself lives in ``step_convert.py``; the single entry point of the repository is
``python main.py`` in the repository root.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from step_convert import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
