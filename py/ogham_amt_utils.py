"""Shared paths, namespaces and small helpers for tei--epidoc-amt.

Everything that more than one step needs lives here: the release number, the
paths, the namespaces, the list of stones and the one writer used for text
files. There is no clock in this repository: the release is a constant, and no
generator calls ``datetime.now()``, so a rebuild changes a file only when the
data or the model changed.
"""
from __future__ import annotations

import re
from pathlib import Path

from rdflib import Namespace

RELEASE = "0.3.0"

GITHUB = "https://github.com/LinkedOpenOgham/tei--epidoc-amt"
BLOB = GITHUB + "/blob/main/"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"                              # inputs: EpiDoc XML, unchanged
OUT = ROOT / "out"                                # products: AMT Turtle and out/README.md
ONTOLOGY = ROOT / "ontology" / "ogham-amt.ttl"    # the domain model, single source of truth
DOCS = ROOT / "docs"                              # GitHub Pages
IMG = DOCS / "diagrams"
BUILD = ROOT / "build"                            # scratch (ignored): pipeline report, runner output

# input file -> output basename; the order is the order of the documentation
STONES = [
    ("S-ARL-001.xml", "gigha1"),          # Gigha 1, CIIC 506  -- most contested
    ("I-COR-001.xml", "coomleagh-east"),  # Coomleagh East, CIIC 55
    ("I-COR-030.xml", "garranes"),        # Garranes, CIIC 81
    ("I-KER-020.xml", "ballinrannig6"),   # Ballinrannig 6, CIIC 153 -- clean
    ("S-MOR-001.xml", "dyke"),            # Dyke -- no CIIC number, one reading with markup
    ("S-BUT-001.xml", "blackwaterfoot-1"),  # Blackwaterfoot 1 -- two inscriptions, readings without @source
    ("S-LKS-X01.xml", "bishop-loch"),     # Bishop Loch -- doubtful record, almost no markup
]

TEI = "http://www.tei-c.org/ns/1.0"
AMT = Namespace("http://academic-meta-tool.xyz/vocab#")
FW = Namespace("http://w3id.org/fw_ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
OGHAM = Namespace("http://ontology.ogham.link/")     # domain concepts, roles, the method
DATA_NS = Namespace("http://data.ogham.link/amt/")   # individuals

# The three FW types AMT.engine knows (amt/fw.py)
FW_VAGUENESS = FW.Vagueness
FW_UNCERTAINTY = FW.Uncertainty
FW_FUZZINESS_WOBBLINESS = FW.FuzzinessWobbliness
TYPE_TAG = {FW_VAGUENESS: "V", FW_UNCERTAINTY: "U", FW_FUZZINESS_WOBBLINESS: "FW", None: ""}
TYPE_CURIE = {FW_VAGUENESS: "fw:Vagueness", FW_UNCERTAINTY: "fw:Uncertainty",
              FW_FUZZINESS_WOBBLINESS: "fw:FuzzinessWobbliness", None: "none"}


NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                9: "nine", 10: "ten"}


def number_word(n: int) -> str:
    """``7`` -> ``seven``; larger numbers stay digits. Keeps the prose in step with ``STONES``."""
    return NUMBER_WORDS.get(n, str(n))


def slug(text: str) -> str:
    """IRI-safe form of a string: runs of anything but letters and digits become one underscore."""
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def rel(path: Path) -> str:
    """``path`` relative to the repository root when it is inside it, else as given."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 with LF line endings and one trailing newline, on every platform."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
