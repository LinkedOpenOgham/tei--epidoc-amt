#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main.py -- convert OG(H)AM EpiDoc editions of ogham stones into Academic Meta
Tool (AMT) Turtle, and document the result in a generated ``data/README.md``.

Single entry point of the ``tei--epidoc-amt`` repository (axis 2 of the Linked
Open Ogham crosswalk). Run from the repo root:

    python py/main.py            # process all stones in STONES, write data/README.md
    python py/main.py --input data/S-ARL-001.xml --output data/gigha1.amt.ttl

For each stone it collects the competing readings and emits an AMT graph:

* ``amt:Concept``  -- the classes ``OghamStone`` and ``Reading``
* ``amt:Role``     -- the relation ``hasReading``
* individuals      -- the stone and each reading, linked with ``amt:instanceOf``
* weighted edges   -- one reified quadruple (``rdf:subject/predicate/object`` +
                      ``amt:weight``) per reading, ready for the AMT reasoning engine
* provenance       -- each reading ``prov:wasAttributedTo`` its editor

A "reading" is either the **current edition** (the ``<div type="edition">``
transliteration) or a **historical** alternative from the apparatus (``<rdg>``).
Stones with a single reading and no apparatus yield one edge with weight 1.0 --
the method adds no doubt where the source shows none.

WEIGHTING RULE (v1). Every reading r gets ``amt:weight(r)`` in [0, 1] from:

1. Reading confidence c(r) -- precision / vagueness.
   * current edition: c = 1 - (0.5*#unclear + 0.7*#supplied + 1.0*#gap) / length,
     mirroring per-character certainties legible 1.0 / <unclear> 0.5 /
     <supplied> 0.3 / <gap> 0.0.
   * historical <rdg>: a proxy -- share of clean characters in the string.
2. Tradition agreement a(r) -- belief across alternatives: fraction of editors
   whose reading clusters with r (similarity >= AGREEMENT_THRESHOLD).

   raw(r) = c(r) * a(r);  amt:weight = raw(r) / sum_r raw(r)   (normalised, sum = 1)
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from lxml import etree
from rdflib import BNode, Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD

# --- repo-root-relative paths -------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"          # inputs (EpiDoc XML)
OUT = ROOT / "out"            # generated outputs (TTL + README)

# --- stones processed by default (input file -> output basename) --------------
STONES = [
    ("S-ARL-001.xml", "gigha1"),          # Gigha 1, CIIC 506  -- most contested
    ("I-COR-001.xml", "coomleagh-east"),  # Coomleagh East, CIIC 55
    ("I-COR-030.xml", "garranes"),        # Garranes, CIIC 81
    ("I-KER-020.xml", "ballinrannig6"),   # Ballinrannig 6, CIIC 153 -- clean
]

# --- documented weighting constants ------------------------------------------
AGREEMENT_THRESHOLD = 0.60             # min. string similarity to cluster two readings
UNCERTAIN_CHARS = set("[]()?/\\-.:")   # editor-introduced doubt markers in a reading string
# per-marker penalty for the current edition = 1 - base character certainty
MARKER_PENALTY = {"unclear": 0.5, "supplied": 0.7, "gap": 1.0}
BASE_CONFIDENCE = {"legible": 1.0, "unclear": 0.5, "supplied": 0.3, "gap": 0.0}
FUZZY_LOGIC = "amt:ProductLogic"       # operator the engine should use when reasoning

# --- namespaces ---------------------------------------------------------------
TEI = "http://www.tei-c.org/ns/1.0"
AMT = Namespace("http://academic-meta-tool.xyz/vocab#")
PROV = Namespace("http://www.w3.org/ns/prov#")
OGHAM = Namespace("http://ontology.ogham.link/")     # domain concepts / roles
DATA_NS = Namespace("http://data.ogham.link/amt/")   # individuals

EDITOR_PREFIXES = {"RHY": "Rhys", "MAC": "Macalister", "DIA": "Diack",
                   "JAC": "Jackson", "FOR": "Forsyth"}


def editor_label(source_id: str) -> str:
    """Expand a resp/source id like 'MAC1945' to 'Macalister 1945'."""
    m = re.match(r"([A-Za-z]+)(\d{4})", source_id or "")
    if not m:
        return source_id or "unknown"
    name = EDITOR_PREFIXES.get(m.group(1).upper(), m.group(1).title())
    return f"{name} {m.group(2)}"


@dataclass
class Reading:
    source_id: str
    editor: str
    text: str
    is_edition: bool = False
    confidence: float = 1.0
    agreement: float = 0.0
    weight: float = 0.0
    signals: dict = field(default_factory=dict)   # extracted doubt signals (for the README)


def _text(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def parse_stone(tree) -> dict:
    ids = {}
    for idno in tree.findall(f".//{{{TEI}}}idno[@type]"):
        ids[idno.get("type")] = (idno.text or "").strip()
    title_el = tree.find(f".//{{{TEI}}}title")
    ids["title"] = _text(title_el) if title_el is not None else ""
    return ids


def _edition_confidence(n_unclear, n_supplied, n_gap, text):
    """c for the current edition; returns (c, length)."""
    length = max(len(re.sub(r"[^A-Za-z]", "", text)), n_unclear + n_supplied + n_gap, 1)
    penalty = (MARKER_PENALTY["unclear"] * n_unclear
               + MARKER_PENALTY["supplied"] * n_supplied
               + MARKER_PENALTY["gap"] * n_gap)
    return round(max(0.0, 1.0 - penalty / length), 4), length


def _proxy_confidence(text):
    """c proxy for a historical <rdg>; returns (c, unclean, length)."""
    stripped = text.replace(" ", "")
    if not stripped:
        return 0.0, 0, 0
    unclean = sum(1 for ch in stripped if ch in UNCERTAIN_CHARS)
    return round(max(0.0, 1.0 - unclean / len(stripped)), 4), unclean, len(stripped)


def parse_readings(tree) -> list[Reading]:
    """Collect the current edition reading plus every active historical <rdg>."""
    readings: list[Reading] = []

    div = tree.find(f".//{{{TEI}}}div[@type='edition'][@subtype='transliteration']")
    if div is None:
        div = tree.find(f".//{{{TEI}}}div[@type='edition']")
    if div is not None:
        ab = div.findall(f".//{{{TEI}}}ab")
        txt = _text(ab[-1]) if ab else _text(div)   # reader-facing transliteration
        if txt:
            resp = (div.get("resp") or "").lstrip("#") or "OGHAM"
            U = len(div.findall(f".//{{{TEI}}}unclear"))
            S = len(div.findall(f".//{{{TEI}}}supplied"))
            G = len(div.findall(f".//{{{TEI}}}gap"))
            c, L = _edition_confidence(U, S, G, txt)
            readings.append(Reading(
                source_id=f"OGHAM_{resp}", editor=f"OG(H)AM edition ({resp})",
                text=txt, is_edition=True, confidence=c,
                signals={"kind": "edition", "unclear": U, "supplied": S, "gap": G, "length": L}))

    for rdg in tree.findall(f".//{{{TEI}}}rdg"):
        src = (rdg.get("source") or rdg.get("resp") or "").lstrip("#")
        txt = _text(rdg)
        if not txt:
            continue
        c, unclean, L = _proxy_confidence(txt)
        readings.append(Reading(
            source_id=src, editor=editor_label(src), text=txt, confidence=c,
            signals={"kind": "proxy", "unclean": unclean, "length": L}))
    return readings


def _normalise_reading(text: str) -> str:
    return re.sub(r"[^A-Za-z]", "", text).upper()


def compute_weights(readings: list[Reading]) -> None:
    norm = [_normalise_reading(r.text) for r in readings]
    n = len(readings)
    for i, r in enumerate(readings):
        cluster = sum(1 for j in range(n)
                      if i == j or SequenceMatcher(None, norm[i], norm[j]).ratio() >= AGREEMENT_THRESHOLD)
        r.agreement = round(cluster / n, 4)
    raw = [r.confidence * r.agreement for r in readings]
    total = sum(raw) or 1.0
    for r, s in zip(readings, raw):
        r.weight = round(s / total, 4)


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def build_graph(stone: dict, readings: list[Reading]) -> Graph:
    g = Graph()
    for pfx, ns in (("amt", AMT), ("prov", PROV), ("ogham", OGHAM),
                    ("data", DATA_NS), ("rdfs", RDFS), ("xsd", XSD)):
        g.bind(pfx, ns)

    g.add((OGHAM.OghamStone, RDF.type, AMT.Concept))
    g.add((OGHAM.OghamStone, RDFS.label, Literal("Ogham stone")))
    g.add((OGHAM.Reading, RDF.type, AMT.Concept))
    g.add((OGHAM.Reading, RDFS.label, Literal("Reading")))
    g.add((OGHAM.hasReading, RDF.type, AMT.Role))
    g.add((OGHAM.hasReading, RDFS.label, Literal("has reading")))
    g.add((OGHAM.hasReading, RDFS.domain, OGHAM.OghamStone))
    g.add((OGHAM.hasReading, RDFS.range, OGHAM.Reading))

    ciic = stone.get("CIIC", stone.get("filename", "stone"))
    stone_uri = DATA_NS[f"stone_{_slug(ciic)}"]
    label = stone.get("title") or f"CIIC {ciic}"
    g.add((stone_uri, AMT.instanceOf, OGHAM.OghamStone))
    g.add((stone_uri, RDFS.label, Literal(f"{label} (CIIC {ciic})")))

    for r in readings:
        r_uri = DATA_NS[f"reading_{_slug(ciic)}_{_slug(r.source_id or r.text)}"]
        g.add((r_uri, AMT.instanceOf, OGHAM.Reading))
        g.add((r_uri, RDFS.label, Literal(r.text)))
        agent = DATA_NS[f"agent_{_slug(r.source_id)}"]
        g.add((agent, RDF.type, PROV.Agent))
        g.add((agent, RDFS.label, Literal(r.editor)))
        g.add((r_uri, PROV.wasAttributedTo, agent))
        q = BNode()
        g.add((q, RDF.subject, stone_uri))
        g.add((q, RDF.predicate, OGHAM.hasReading))
        g.add((q, RDF.object, r_uri))
        g.add((q, AMT.weight, Literal(f"{r.weight:.4f}", datatype=XSD.decimal)))
    return g


# --- README rendering (dynamic) ----------------------------------------------
def _signals_str(r: Reading) -> str:
    s = r.signals
    if s.get("kind") == "edition":
        return f"{s['unclear']}× `<unclear>`, {s['supplied']}× `<supplied>`, {s['gap']}× `<gap>`"
    return f"proxy: {s['unclean']} editor-marked char(s) of {s['length']}"


def _c_formula(r: Reading) -> str:
    s = r.signals
    if s.get("kind") == "edition":
        return (f"1 − (0.5·{s['unclear']} + 0.7·{s['supplied']} + 1.0·{s['gap']}) / "
                f"{s['length']} = **{r.confidence:.2f}**")
    return f"1 − {s['unclean']} / {s['length']} = **{r.confidence:.2f}**"


def write_data_readme(results: list[tuple[dict, list[Reading], str]]) -> None:
    L = []
    add = L.append
    add("# `out/` — extracted doubt and its AMT modelling\n")
    add("> **Generated file** — produced by `python py/main.py`. Do not edit by hand; "
        "it adapts to the EpiDoc inputs and to the weighting constants in `py/main.py`.\n")

    add("## 1. How doubt is extracted from an inscription\n")
    add("Each competing reading of a stone becomes one weighted edge. Two kinds of reading "
        "are read out of the EpiDoc file:\n")
    add("- the **current edition** — the `<div type=\"edition\">` transliteration; and")
    add("- every active **historical reading** in the apparatus — `<rdg>` "
        "(readings commented out in the XML are ignored).\n")
    add("The editorial doubt markup is mapped to per-character base certainties:\n")
    add("| EpiDoc signal | meaning | base certainty | penalty (1 − certainty) |")
    add("|---|---|---|---|")
    add(f"| legible glyph | securely read | {BASE_CONFIDENCE['legible']:.1f} | 0.0 |")
    add(f"| `<unclear>` | not clearly legible | {BASE_CONFIDENCE['unclear']:.1f} | {MARKER_PENALTY['unclear']:.1f} |")
    add(f"| `<supplied>` | editorially restored | {BASE_CONFIDENCE['supplied']:.1f} | {MARKER_PENALTY['supplied']:.1f} |")
    add(f"| `<gap>` | lost, not restored | {BASE_CONFIDENCE['gap']:.1f} | {MARKER_PENALTY['gap']:.1f} |\n")

    add("## 2. How the reading confidence c is computed\n")
    add("**Current edition** — from the markup counts (fuzzy-AND ≈ mean penalty over the string):\n")
    add("```\nc = 1 − (0.5·#unclear + 0.7·#supplied + 1.0·#gap) / length\n```\n")
    add("**Historical `<rdg>`** — usually no per-character markup, so a proxy from the "
        "editor-introduced doubt characters (brackets, slashes, dashes, `?`):\n")
    add("```\nc = 1 − (editor-marked chars) / length\n```\n")
    add("The **tradition agreement** `a` = fraction of editors whose reading clusters with r "
        f"(string similarity ≥ {AGREEMENT_THRESHOLD}). The edge weight is the normalised product\n")
    add("```\namt:weight(r) = c(r)·a(r) / Σ c·a          (Σ over the alternatives = 1)\n```\n")

    add("## 3. How it is modelled with AMT\n")
    add("Every reading is an `amt:Concept` individual (`amt:instanceOf ogham:Reading`); the stone "
        "`hasReading` each of them as a **reified quadruple** carrying the `amt:weight`; each reading "
        "is `prov:wasAttributedTo` its editor. The normalised weights are a belief distribution, "
        "bridged to CIDOC CRM's argumentation model **CRMinf (I2 Belief)**. Literal shape:\n")
    add("```turtle\n[] rdf:subject   data:stone_506 ;\n"
        "   rdf:predicate ogham:hasReading ;\n"
        "   rdf:object    data:reading_506_MAC1945 ;\n"
        "   amt:weight    \"0.2727\"^^xsd:decimal .\n```\n")
    add(f"The reasoning engine (`n4o-rse/amt-engine`) then combines these weights with the "
        f"`{FUZZY_LOGIC}` operator when it applies inference axioms.\n")

    add("## 4. Per stone\n")
    for stone, readings, out in results:
        ciic = stone.get("CIIC", "?")
        title = stone.get("title", "?")
        n_ed = sum(1 for r in readings if r.is_edition)
        add(f"### {title} (CIIC {ciic})\n")
        add(f"`{out}` — {len(readings)} reading(s): {n_ed} edition + {len(readings) - n_ed} historical.\n")
        add("| reading | editor | extracted doubt | c | a | amt:weight |")
        add("|---|---|---|---|---|---|")
        for r in sorted(readings, key=lambda x: -x.weight):
            txt = r.text if len(r.text) <= 34 else r.text[:31] + "…"
            add(f"| {txt} | {r.editor} | {_signals_str(r)} | {r.confidence:.2f} | "
                f"{r.agreement:.2f} | **{r.weight:.4f}** |")
        add("\n*c per reading:*\n")
        for r in sorted(readings, key=lambda x: -x.weight):
            add(f"- {r.editor}: c = {_c_formula(r)}")
        add("\n*AMT edges (stone → reading @ weight):*\n")
        for r in sorted(readings, key=lambda x: -x.weight):
            add(f"- `stone_{_slug(ciic)}` —`hasReading`→ *{r.editor}* · **weight {r.weight:.4f}**")
        add("")

    (OUT / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"  -> wrote {(OUT / 'README.md').relative_to(ROOT)}")


def run_shacl(ttl_path: Path, shapes: Path, ontology: Path) -> bool:
    from pyshacl import validate
    ok, _, text = validate(data_graph=str(ttl_path), shacl_graph=str(shapes),
                           ont_graph=str(ontology), inference="rdfs")
    if not ok:
        print(text)
    return ok


def process(input_path: Path, output_path: Path, shapes=None, ontology=None):
    tree = etree.parse(str(input_path))
    stone = parse_stone(tree)
    readings = parse_readings(tree)
    if not readings:
        raise SystemExit(f"No readings found in {input_path.name}")
    compute_weights(readings)

    n_ed = sum(1 for r in readings if r.is_edition)
    print(f"\n{stone.get('title', '?')} (CIIC {stone.get('CIIC', '?')}) "
          f"-- {len(readings)} reading(s): {n_ed} edition + {len(readings) - n_ed} historical")
    for r in sorted(readings, key=lambda x: -x.weight):
        tag = "EDITION" if r.is_edition else "hist.  "
        print(f"  [{tag}] {r.editor:22} c={r.confidence:.2f} a={r.agreement:.2f} "
              f"w={r.weight:.4f}  {r.text[:46]}")

    g = build_graph(stone, readings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(output_path), format="turtle")
    status = ""
    if shapes and ontology:
        status = "  SHACL: " + ("VALID" if run_shacl(output_path, shapes, ontology) else "INVALID")
    print(f"  -> wrote {output_path.relative_to(ROOT)}  ({len(g)} triples){status}")
    return stone, readings, output_path.name


def main() -> None:
    ap = argparse.ArgumentParser(description="EpiDoc -> AMT Turtle (Linked Open Ogham, axis 2)")
    ap.add_argument("--input", type=Path, help="single EpiDoc file (default: all stones in STONES)")
    ap.add_argument("--output", type=Path, help="output Turtle file (single-file mode only)")
    ap.add_argument("--shapes", type=Path, help="amt-shapes.ttl (enables optional SHACL validation)")
    ap.add_argument("--ontology", type=Path, help="amt.ttl (for SHACL rdfs inference)")
    args = ap.parse_args()

    if args.input:
        out = args.output or (OUT / (args.input.stem + ".amt.ttl"))
        process(args.input, out, args.shapes, args.ontology)
    else:
        results = [process(DATA / f, OUT / f"{b}.amt.ttl", args.shapes, args.ontology)
                   for f, b in STONES]
        write_data_readme(results)
    if not (args.shapes and args.ontology):
        print("\n(SHACL skipped -- pass --shapes amt-shapes.ttl --ontology amt.ttl to validate)")


if __name__ == "__main__":
    main()
