#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step "convert": OG(H)AM EpiDoc editions of ogham stones -> Academic Meta Tool
(AMT) Turtle, and the generated ``out/README.md``.

Axis 2 (vagueness modelling) of the Linked Open Ogham crosswalk. Run from the
repository root with ``python main.py --only convert``, or on its own:

    python py/step_convert.py        # all stones in STONES, writes out/*.amt.ttl and out/README.md
    python py/step_convert.py --input data/S-ARL-001.xml --output out/gigha1.amt.ttl

(``python py/main.py`` still works and calls this module.)

For each stone it collects the competing readings and emits an AMT graph:

* ``amt:Concept``  -- the classes ``OghamStone`` and ``Reading`` (ontology/ogham-amt.ttl)
* ``amt:Role``     -- the relation ``hasReading``
* individuals      -- the stone and each reading, linked with ``amt:instanceOf``
* hextuples        -- one reified statement per reading: ``rdf:subject / predicate /
                      object``, ``amt:weight``, ``fw:hasType``, ``fw:hasMethod``, and
                      ``fw:derivedFrom`` the reading string as ``fw:TextEvidence``
* provenance       -- each reading ``prov:wasAttributedTo`` its editor

A "reading" is either the **current edition** (the ``<div type="edition">``
transliteration) or a **historical** alternative from the apparatus (``<rdg>``).
A stone with a single reading and no apparatus yields one statement with weight
1.0: the method adds no doubt where the source shows none.

WEIGHTING RULE (v1, unchanged since the first release). Every reading r gets
``amt:weight(r)`` in [0, 1] from:

1. Reading confidence c(r) -- precision / vagueness.
   * current edition: c = 1 - (0.5*#unclear + 0.7*#supplied + 1.0*#gap) / length.
   * historical <rdg>: a proxy -- share of clean characters in the string.
2. Tradition agreement a(r) -- belief across alternatives: fraction of readings
   that cluster with r (similarity >= AGREEMENT_THRESHOLD).

   raw(r) = c(r) * a(r);  amt:weight = raw(r) / sum_r raw(r)   (normalised, sum = 1)

FW TYPE (new in 0.2.0). The type names the factor(s) that pulled raw(r) below 1:
c < 1 is imprecision (``fw:Vagueness``), a < 1 is disagreement among the readings
(``fw:Uncertainty``), both is ``fw:FuzzinessWobbliness``. Neither: no type is
written, and AMT reads a statement without type as ``fw:Vagueness``. The weights
themselves are not touched by this.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lxml import etree  # noqa: E402
from rdflib import Graph, Literal  # noqa: E402
from rdflib.namespace import RDF, RDFS, XSD  # noqa: E402

from ogham_amt_utils import (  # noqa: E402
    AMT, DATA, DATA_NS, FW, FW_FUZZINESS_WOBBLINESS, FW_UNCERTAINTY, FW_VAGUENESS, OGHAM, ONTOLOGY,
    OUT, PROV, SKOS, STONES, TEI, TYPE_CURIE, TYPE_TAG, rel, slug, write_text,
)

# --- documented weighting constants ------------------------------------------
AGREEMENT_THRESHOLD = 0.60             # min. string similarity to cluster two readings
UNCERTAIN_CHARS = set("[]()?/\\-.:")   # editor-introduced doubt markers in a reading string
# per-marker penalty for the current edition = 1 - base character certainty
MARKER_PENALTY = {"unclear": 0.5, "supplied": 0.7, "gap": 1.0}
BASE_CONFIDENCE = {"legible": 1.0, "unclear": 0.5, "supplied": 0.3, "gap": 0.0}
FUZZY_LOGIC = "amt:ProductLogic"       # operator the engine should use if axioms are added later
METHOD = OGHAM.ConfidenceAgreementRule  # fw:hasMethod of every statement (ontology/ogham-amt.ttl)

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


def reading_type(r: Reading):
    """FW type of the statement of ``r``: which factor pulled raw(r) below 1.

    c < 1   imprecision in the reading itself        -> fw:Vagueness
    a < 1   other readings disagree                  -> fw:Uncertainty
    both                                             -> fw:FuzzinessWobbliness
    neither                                          -> None (written as no type; AMT reads Vagueness)
    """
    vague, uncertain = r.confidence < 1.0, r.agreement < 1.0
    if vague and uncertain:
        return FW_FUZZINESS_WOBBLINESS
    if uncertain:
        return FW_UNCERTAINTY
    if vague:
        return FW_VAGUENESS
    return None


def analyse(input_path: Path) -> tuple[dict, list[Reading]]:
    """Parse one EpiDoc file: the stone's identifiers and its weighted readings."""
    tree = etree.parse(str(input_path))
    stone = parse_stone(tree)
    readings = parse_readings(tree)
    if not readings:
        raise SystemExit(f"No readings found in {input_path.name}")
    compute_weights(readings)
    return stone, readings


def local_names(stone: dict, readings: list[Reading]) -> list[dict]:
    """The IRI local names of every reading, its statement and its evidence node.

    Used by ``build_graph`` and by the documentation, so that both name the same
    IRIs. Two readings with the same source id get ``_2``, ``_3`` ... rather than
    silently merging into one node.
    """
    ciic = slug(stone.get("CIIC", stone.get("filename", "stone")))
    seen: dict[str, int] = {}
    names = []
    for r in readings:
        key = slug(r.source_id or r.text)
        seen[key] = seen.get(key, 0) + 1
        suffix = "" if seen[key] == 1 else f"_{seen[key]}"
        names.append({
            "reading": f"reading_{ciic}_{key}{suffix}",
            "statement": f"stmt_{ciic}_{key}{suffix}",
            "evidence": f"evidence_{ciic}_{key}{suffix}",
            "agent": f"agent_{slug(r.source_id)}",
        })
    return names


def stone_iri(stone: dict):
    return DATA_NS[f"stone_{slug(stone.get('CIIC', stone.get('filename', 'stone')))}"]


def build_graph(stone: dict, readings: list[Reading]) -> Graph:
    g = Graph()
    g.parse(str(ONTOLOGY), format="turtle")          # concepts, role, method
    for pfx, ns in (("amt", AMT), ("fw", FW), ("ogham", OGHAM), ("data", DATA_NS),
                    ("prov", PROV), ("rdfs", RDFS), ("skos", SKOS), ("xsd", XSD)):
        g.bind(pfx, ns)

    ciic = stone.get("CIIC", stone.get("filename", "stone"))
    s_uri = stone_iri(stone)
    label = stone.get("title") or f"CIIC {ciic}"
    g.add((s_uri, AMT.instanceOf, OGHAM.OghamStone))
    g.add((s_uri, RDFS.label, Literal(f"{label} (CIIC {ciic})")))

    for r, n in zip(readings, local_names(stone, readings)):
        r_uri = DATA_NS[n["reading"]]
        g.add((r_uri, AMT.instanceOf, OGHAM.Reading))
        g.add((r_uri, RDFS.label, Literal(r.text)))
        agent = DATA_NS[n["agent"]]
        g.add((agent, RDF.type, PROV.Agent))
        g.add((agent, RDFS.label, Literal(r.editor)))
        g.add((r_uri, PROV.wasAttributedTo, agent))

        st, ev = DATA_NS[n["statement"]], DATA_NS[n["evidence"]]
        g.add((st, RDF.subject, s_uri))
        g.add((st, RDF.predicate, OGHAM.hasReading))
        g.add((st, RDF.object, r_uri))
        g.add((st, AMT.weight, Literal(f"{r.weight:.4f}", datatype=XSD.decimal)))
        t = reading_type(r)
        if t is not None:
            g.add((st, FW.hasType, t))
        g.add((st, FW.hasMethod, METHOD))
        g.add((st, FW.derivedFrom, ev))
        g.add((ev, RDF.type, FW.TextEvidence))
        g.add((ev, FW.sourceString, Literal(r.text)))
    return g


# --- out/README.md rendering (generated) -------------------------------------
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


def hextuple_example(results) -> str:
    """The Turtle of one real statement: the heaviest reading of the first stone with alternatives."""
    for stone, readings, _ in results:
        if len(readings) > 1:
            names = local_names(stone, readings)
            i = max(range(len(readings)), key=lambda k: readings[k].weight)
            r, n = readings[i], names[i]
            lines = [f"data:{n['statement']}",
                     f"    rdf:subject    data:stone_{slug(stone.get('CIIC', 'stone'))} ;",
                     "    rdf:predicate  ogham:hasReading ;",
                     f"    rdf:object     data:{n['reading']} ;",
                     f"    amt:weight     {r.weight:.4f} ;"]
            t = reading_type(r)
            if t is not None:
                lines.append(f"    fw:hasType     {TYPE_CURIE[t]} ;")
            lines += ["    fw:hasMethod   ogham:ConfidenceAgreementRule ;",
                      f"    fw:derivedFrom data:{n['evidence']} .", "",
                      f"data:{n['evidence']} a fw:TextEvidence ;",
                      f"    fw:sourceString \"{r.text}\" ."]
            return "\n".join(lines)
    return ""


def write_out_readme(results: list[tuple[dict, list[Reading], str]]) -> None:
    L = []
    add = L.append
    add("# `out/` — extracted doubt and its AMT modelling\n")
    add("> **Generated file** — produced by `python main.py` (step `convert`). Do not edit by hand; "
        "it adapts to the EpiDoc inputs and to the weighting constants in `py/step_convert.py`.\n")

    add("## 1. How doubt is extracted from an inscription\n")
    add("Each competing reading of a stone becomes one weighted statement. Two kinds of reading "
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
    add("The **tradition agreement** `a` = fraction of readings that cluster with r "
        f"(string similarity ≥ {AGREEMENT_THRESHOLD}). The weight is the normalised product\n")
    add("```\namt:weight(r) = c(r)·a(r) / Σ c·a          (Σ over the alternatives = 1)\n```\n")

    add("## 3. How the FW type is set\n")
    add("The type names the factor that pulled the raw weight below 1. It does not change the weight.\n")
    add("| c < 1 (imprecise reading) | a < 1 (other readings disagree) | `fw:hasType` |")
    add("|---|---|---|")
    add("| no | no | none written; AMT reads a statement without type as `fw:Vagueness` |")
    add("| yes | no | `fw:Vagueness` |")
    add("| no | yes | `fw:Uncertainty` |")
    add("| yes | yes | `fw:FuzzinessWobbliness` |\n")

    add("## 4. How it is modelled with AMT\n")
    add("Every reading is an `amt:Concept` individual (`amt:instanceOf ogham:Reading`); the stone "
        "`hasReading` each of them as a **hextuple**: a reified statement (`rdf:subject`, `rdf:predicate`, "
        "`rdf:object`) carrying `amt:weight`, `fw:hasType` and `fw:hasMethod`, with the reading string "
        "as `fw:TextEvidence` (`fw:derivedFrom`). Each reading is `prov:wasAttributedTo` its editor. "
        "The normalised weights are a belief distribution, bridged to CIDOC CRM's argumentation model "
        "**CRMinf (I2 Belief)**. Literal shape, taken from the data:\n")
    add("```turtle\n" + hextuple_example(results) + "\n```\n")
    add("The graphs contain no axioms. The reasoning engine "
        "([`alpaca-fair-framework/amt-engine`](https://github.com/alpaca-fair-framework/amt-engine)) "
        "validates and exports them; it has nothing to derive until axioms are added, and would then combine "
        f"weights with the logic of the axiom (for example `{FUZZY_LOGIC}`).\n")

    add("## 5. Per stone\n")
    for stone, readings, out in results:
        ciic = stone.get("CIIC", "?")
        title = stone.get("title", "?")
        n_ed = sum(1 for r in readings if r.is_edition)
        add(f"### {title} (CIIC {ciic})\n")
        add(f"`{out}` — {len(readings)} reading(s): {n_ed} edition + {len(readings) - n_ed} historical.\n")
        add("| reading | editor | extracted doubt | c | a | amt:weight | type |")
        add("|---|---|---|---|---|---|---|")
        for r in sorted(readings, key=lambda x: (-x.weight, x.source_id)):
            txt = r.text if len(r.text) <= 34 else r.text[:31] + "…"
            add(f"| {txt} | {r.editor} | {_signals_str(r)} | {r.confidence:.2f} | "
                f"{r.agreement:.2f} | **{r.weight:.4f}** | {TYPE_TAG[reading_type(r)] or '-'} |")
        add("\n*c per reading:*\n")
        for r in sorted(readings, key=lambda x: (-x.weight, x.source_id)):
            add(f"- {r.editor}: c = {_c_formula(r)}")
        add("\n*AMT statements (stone → reading @ weight):*\n")
        for r in sorted(readings, key=lambda x: (-x.weight, x.source_id)):
            add(f"- `stone_{slug(ciic)}` —`hasReading`→ *{r.editor}* · **weight {r.weight:.4f}**")
        add("")
    add("*Type: V = `fw:Vagueness`, U = `fw:Uncertainty`, FW = `fw:FuzzinessWobbliness`, "
        "`-` = no type written.*\n")

    write_text(OUT / "README.md", "\n".join(L))
    print(f"  -> wrote {rel(OUT / 'README.md')}")


def run_shacl(ttl_path: Path, shapes: Path, ontology: Path) -> bool:
    from pyshacl import validate
    ok, _, text = validate(data_graph=str(ttl_path), shacl_graph=str(shapes),
                           ont_graph=str(ontology), inference="rdfs", advanced=True)
    if not ok:
        print(text)
    return ok


def process(input_path: Path, output_path: Path, shapes=None, ontology=None):
    stone, readings = analyse(input_path)

    n_ed = sum(1 for r in readings if r.is_edition)
    print(f"\n{stone.get('title', '?')} (CIIC {stone.get('CIIC', '?')}) "
          f"-- {len(readings)} reading(s): {n_ed} edition + {len(readings) - n_ed} historical")
    for r in sorted(readings, key=lambda x: (-x.weight, x.source_id)):
        tag = "EDITION" if r.is_edition else "hist.  "
        print(f"  [{tag}] {r.editor:22} c={r.confidence:.2f} a={r.agreement:.2f} "
              f"w={r.weight:.4f} {TYPE_TAG[reading_type(r)]:>2}  {r.text[:46]}")

    g = build_graph(stone, readings)
    write_text(output_path, g.serialize(format="turtle"))
    status = ""
    if shapes and ontology:
        status = "  SHACL: " + ("VALID" if run_shacl(output_path, shapes, ontology) else "INVALID")
    print(f"  -> wrote {rel(output_path)}  ({len(g)} triples){status}")
    return stone, readings, output_path.name


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EpiDoc -> AMT Turtle (Linked Open Ogham, axis 2)")
    ap.add_argument("--input", type=Path, help="single EpiDoc file (default: all stones in STONES)")
    ap.add_argument("--output", type=Path, help="output Turtle file (single-file mode only)")
    ap.add_argument("--shapes", type=Path, help="amt-shapes.ttl of the engine (enables optional SHACL validation)")
    ap.add_argument("--ontology", type=Path, help="amt.ttl of the engine (for SHACL rdfs inference)")
    args = ap.parse_args(argv)

    if args.input:
        out = args.output or (OUT / (args.input.stem + ".amt.ttl"))
        process(args.input, out, args.shapes, args.ontology)
    else:
        results = [process(DATA / f, OUT / f"{b}.amt.ttl", args.shapes, args.ontology)
                   for f, b in STONES]
        write_out_readme(results)
    if not (args.shapes and args.ontology):
        print("\n(SHACL skipped -- pass --shapes amt-shapes.ttl --ontology amt.ttl to validate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
