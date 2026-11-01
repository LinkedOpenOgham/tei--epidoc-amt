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
    CERT_FACTOR, OUT, OUT_V2, PROV, SKOS, STONES, TEI, TYPE_CURIE, TYPE_TAG, record_status, rel, slug, write_text,
)

# --- documented weighting constants ------------------------------------------
AGREEMENT_THRESHOLD = 0.60             # min. string similarity to cluster two readings
UNCERTAIN_CHARS = set("[]()?/\\-.:")   # editor-introduced doubt markers in a reading string
# per-marker penalty for the current edition = 1 - base character certainty
MARKER_PENALTY = {"unclear": 0.5, "supplied": 0.7, "gap": 1.0}
BASE_CONFIDENCE = {"legible": 1.0, "unclear": 0.5, "supplied": 0.3, "gap": 0.0}
FUZZY_LOGIC = "amt:ProductLogic"       # operator the engine should use if axioms are added later
METHOD = OGHAM.ConfidenceAgreementRule  # fw:hasMethod of every statement under rule v1 (ontology/ogham-amt.ttl)
METHODS = {"v1": METHOD, "v2": OGHAM.ConfidenceCertAgreementRule}

EDITOR_PREFIXES = {"RHY": "Rhys", "MAC": "Macalister", "DIA": "Diack",
                   "JAC": "Jackson", "FOR": "Forsyth"}


def editor_label(source_id: str) -> str:
    """Expand a resp/source id like 'MAC1945' to 'Macalister 1945'."""
    if not source_id:
        return "no editor named"
    m = re.match(r"([A-Za-z]+)(\d{4})", source_id)
    if not m:
        return source_id
    name = EDITOR_PREFIXES.get(m.group(1).upper(), m.group(1).title())
    return f"{name} {m.group(2)}"


@dataclass
class Reading:
    source_id: str
    editor: str
    text: str
    is_edition: bool = False
    inscription: int | None = None   # n of the inscription in a file that holds several; None otherwise
    cert: str | None = None          # @cert of the edition div (low, medium, high), if it has one
    confidence: float = 1.0
    agreement: float = 0.0
    weight: float = 0.0
    signals: dict = field(default_factory=dict)   # extracted doubt signals (for the README)


def _text(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def parse_stone(tree) -> dict:
    ids = {}
    for idno in tree.findall(f".//{{{TEI}}}idno[@type]"):
        value = (idno.text or "").strip()
        if value:                                   # <idno type="CIIC"/> is empty for stones without a number
            ids[idno.get("type")] = value
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


ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6}


def stone_id(stone: dict) -> str:
    """The identifier that names the stone's IRIs: its CIIC number, else its file name (S-MOR-001)."""
    return stone.get("CIIC") or stone.get("filename") or "stone"


def stone_ref(stone: dict) -> str:
    """How a person cites the stone: ``CIIC 506``, or the file name where there is no CIIC number."""
    return f"CIIC {stone['CIIC']}" if stone.get("CIIC") else stone_id(stone)


def inscription_label(stone: dict, n) -> str:
    """Heading of one reading unit: the stone, plus the inscription where the file holds several."""
    base = f"{stone.get('title', '')} ({stone_ref(stone)})"
    return base if n is None else f"{stone.get('title', '')}, inscription {n} ({stone_ref(stone)})"


def _edition_divs(tree) -> list[tuple[int | None, object]]:
    """The non-empty transliteration editions of the file with their inscription number.

    The number is the ``n`` of the ``textpart`` of the ogham-script edition that precedes the
    transliteration (a commented-out third inscription therefore leaves a gap, as in the file).
    """
    divs = tree.findall(f".//{{{TEI}}}div[@type='edition']")
    pairs, last_n = [], None
    for d in divs:
        if d.get("subtype") == "ogham":
            part = d.find(f".//{{{TEI}}}div[@type='textpart']")
            last_n = part.get("n") if part is not None else None
        elif d.get("subtype") == "transliteration":
            ab = d.findall(f".//{{{TEI}}}ab")
            if _text(ab[-1] if ab else d):
                pairs.append((last_n, d))
    if not pairs and divs:                          # no subtype: first edition div, as before
        pairs = [(None, divs[0])]
    return pairs


def _rdg_inscription(rdg) -> int:
    """The inscription an apparatus reading belongs to, from the ordinal in the note of its ``<app>``."""
    app = next((a for a in rdg.iterancestors() if etree.QName(a).localname == "app"), None)
    note = app.find(f"{{{TEI}}}note") if app is not None else None
    m = re.search(r"\b(%s)\s+inscription" % "|".join(ORDINALS), _text(note).lower() if note is not None else "")
    if not m:
        raise SystemExit("A file with several inscriptions has a <rdg> whose <app> note does not say which "
                         f"inscription it belongs to: {_text(rdg)!r}")
    return ORDINALS[m.group(1)]


def parse_readings(tree) -> list[Reading]:
    """Collect the current edition reading(s) plus every active historical <rdg>.

    A file with one inscription (the usual case) yields readings that compete with one another. A
    file with several (Blackwaterfoot 1) yields them per inscription: the readings of the first and
    of the second inscription are not alternatives of each other, so ``Reading.inscription`` keeps
    them apart and the weights are computed within each.
    """
    readings: list[Reading] = []

    editions = _edition_divs(tree)
    several = len(editions) > 1
    for n, div in editions:
        ab = div.findall(f".//{{{TEI}}}ab")
        txt = _text(ab[-1]) if ab else _text(div)   # reader-facing transliteration
        resp = (div.get("resp") or "").lstrip("#") or "OGHAM"
        U = len(div.findall(f".//{{{TEI}}}unclear"))
        S = len(div.findall(f".//{{{TEI}}}supplied"))
        G = len(div.findall(f".//{{{TEI}}}gap"))
        c, L = _edition_confidence(U, S, G, txt)
        readings.append(Reading(
            source_id=f"OGHAM_{resp}", editor=f"OG(H)AM edition ({resp})",
            text=txt, is_edition=True, confidence=c,
            inscription=int(n) if several and n else None,
            cert=div.get("cert") if div.get("cert") in CERT_FACTOR else None,
            signals={"kind": "edition", "unclear": U, "supplied": S, "gap": G, "length": L}))

    for rdg in tree.findall(f".//{{{TEI}}}rdg"):
        src = (rdg.get("source") or rdg.get("resp") or "").lstrip("#")
        txt = _text(rdg)
        if not txt:
            continue
        c, unclean, L = _proxy_confidence(txt)
        readings.append(Reading(
            source_id=src, editor=editor_label(src), text=txt, confidence=c,
            inscription=_rdg_inscription(rdg) if several else None,
            signals={"kind": "proxy", "unclean": unclean, "length": L}))
    return readings


def units(readings: list[Reading]) -> list[tuple[int | None, list[Reading]]]:
    """The readings grouped by inscription, in order of first appearance (one group for most stones)."""
    order: list[int | None] = []
    for r in readings:
        if r.inscription not in order:
            order.append(r.inscription)
    return [(n, [r for r in readings if r.inscription == n]) for n in sorted(order, key=lambda k: (k is None, k))]


def _normalise_reading(text: str) -> str:
    return re.sub(r"[^A-Za-z]", "", text).upper()


def compute_weights(readings: list[Reading]) -> None:
    """Weights within each inscription: readings of different inscriptions are not alternatives."""
    for _, group in units(readings):
        norm = [_normalise_reading(r.text) for r in group]
        n = len(group)
        for i, r in enumerate(group):
            cluster = sum(1 for j in range(n)
                          if i == j or SequenceMatcher(None, norm[i], norm[j]).ratio() >= AGREEMENT_THRESHOLD)
            r.agreement = round(cluster / n, 4)
        raw = [r.confidence * r.agreement for r in group]
        total = sum(raw) or 1.0
        for r, share in zip(group, raw):
            r.weight = round(share / total, 4)


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


def analyse(input_path: Path, rule: str = "v1") -> tuple[dict, list[Reading]]:
    """Parse one EpiDoc file: the stone's identifiers and its weighted readings.

    Rule v1 is the original rule. Rule v2 multiplies c of an edition that carries ``@cert`` by the
    GSAS degree of that level (``CERT_FACTOR``); the readings of the apparatus have no ``@cert``.
    """
    tree = etree.parse(str(input_path))
    stone = parse_stone(tree)
    readings = parse_readings(tree)
    if not readings:
        raise SystemExit(f"No readings found in {input_path.name}")
    if rule == "v2":
        for r in readings:
            if r.cert:
                r.signals["k"] = CERT_FACTOR[r.cert]
                r.confidence = round(r.confidence * CERT_FACTOR[r.cert], 4)
    compute_weights(readings)
    return stone, readings


def local_names(stone: dict, readings: list[Reading]) -> list[dict]:
    """The IRI local names of every reading, its statement and its evidence node.

    Used by ``build_graph`` and by the documentation, so that both name the same
    IRIs. Two readings with the same source id get ``_2``, ``_3`` ... rather than
    silently merging into one node. In a file with several inscriptions the names
    carry the inscription (``..._i2_FOR1996``).
    """
    ident = slug(stone_id(stone))
    seen: dict[str, int] = {}
    names = []
    for r in readings:
        key = slug(r.source_id or r.text)
        if r.inscription is not None:
            key = f"i{r.inscription}_{key}"
        seen[key] = seen.get(key, 0) + 1
        suffix = "" if seen[key] == 1 else f"_{seen[key]}"
        names.append({
            "reading": f"reading_{ident}_{key}{suffix}",
            "statement": f"stmt_{ident}_{key}{suffix}",
            "evidence": f"evidence_{ident}_{key}{suffix}",
            "kind": f"kind_{ident}_{key}{suffix}",
            "attribution": f"attr_{ident}_{key}{suffix}",
            "reverse": f"rev_{ident}_{key}{suffix}",
            "agent": f"agent_{slug(r.source_id)}" if r.source_id else None,
        })
    return names


def stone_iri(stone: dict):
    return DATA_NS[f"stone_{slug(stone_id(stone))}"]


def subject_iri(stone: dict, inscription):
    """The subject of ``hasReading``: the stone, or its inscription where the file holds several."""
    if inscription is None:
        return stone_iri(stone)
    return DATA_NS[f"inscription_{slug(stone_id(stone))}_{inscription}"]


def build_graph(stone: dict, readings: list[Reading], rule: str = "v1") -> Graph:
    g = Graph()
    g.parse(str(ONTOLOGY), format="turtle")          # concepts, role, method
    for pfx, ns in (("amt", AMT), ("fw", FW), ("ogham", OGHAM), ("data", DATA_NS),
                    ("prov", PROV), ("rdfs", RDFS), ("skos", SKOS), ("xsd", XSD)):
        g.bind(pfx, ns)

    s_uri = stone_iri(stone)
    g.add((s_uri, AMT.instanceOf, OGHAM.OghamStone))
    g.add((s_uri, RDFS.label, Literal(inscription_label(stone, None))))
    g.add((s_uri, OGHAM.recordStatus, Literal(record_status(stone.get("filename", "")))))
    for n, _ in units(readings):
        if n is not None:                            # a file with several inscriptions
            i_uri = subject_iri(stone, n)
            g.add((i_uri, AMT.instanceOf, OGHAM.Inscription))
            g.add((i_uri, RDFS.label, Literal(inscription_label(stone, n))))
            g.add((s_uri, OGHAM.hasInscription, i_uri))

    for r, n in zip(readings, local_names(stone, readings)):
        r_uri = DATA_NS[n["reading"]]
        g.add((r_uri, AMT.instanceOf, OGHAM.Reading))
        g.add((r_uri, RDFS.label, Literal(r.text)))
        if n["agent"]:                               # a <rdg> without @source has no attributable editor
            agent = DATA_NS[n["agent"]]
            g.add((agent, RDF.type, PROV.Agent))
            g.add((agent, AMT.instanceOf, OGHAM.Editor))
            g.add((agent, RDFS.label, Literal(r.editor)))
            g.add((r_uri, PROV.wasAttributedTo, agent))
            att = DATA_NS[n["attribution"]]          # the weighted link the editor chains run on
            g.add((att, RDF.subject, r_uri))
            g.add((att, RDF.predicate, OGHAM.attributedTo))
            g.add((att, RDF.object, agent))
            g.add((att, AMT.weight, Literal("1.0000", datatype=XSD.decimal)))

        st, ev = DATA_NS[n["statement"]], DATA_NS[n["evidence"]]
        g.add((st, RDF.subject, subject_iri(stone, r.inscription)))
        g.add((st, RDF.predicate, OGHAM.hasReading if r.inscription is None else OGHAM.hasInscriptionReading))
        g.add((st, RDF.object, r_uri))
        g.add((st, AMT.weight, Literal(f"{r.weight:.4f}", datatype=XSD.decimal)))
        t = reading_type(r)
        if t is not None:
            g.add((st, FW.hasType, t))
        g.add((st, FW.hasMethod, METHODS[rule]))
        g.add((st, FW.derivedFrom, ev))
        g.add((ev, RDF.type, FW.TextEvidence))
        g.add((ev, FW.sourceString, Literal(r.text)))
        rv = DATA_NS[n["reverse"]]                   # the other direction, same weight (the engine has no inverse construct)
        g.add((rv, RDF.subject, r_uri))
        g.add((rv, RDF.predicate, OGHAM.readingOf))
        g.add((rv, RDF.object, subject_iri(stone, r.inscription)))
        g.add((rv, AMT.weight, Literal(f"{r.weight:.4f}", datatype=XSD.decimal)))
        if r.inscription is None:                    # the finer role, with the same weight: what the subsumption axioms use
            kd = DATA_NS[n["kind"]]
            g.add((kd, RDF.subject, s_uri))
            g.add((kd, RDF.predicate, OGHAM.hasEditionReading if r.is_edition else OGHAM.hasHistoricalReading))
            g.add((kd, RDF.object, r_uri))
            g.add((kd, AMT.weight, Literal(f"{r.weight:.4f}", datatype=XSD.decimal)))
    return g


# --- out/README.md rendering (generated) -------------------------------------
def _signals_str(r: Reading) -> str:
    s = r.signals
    if s.get("kind") == "edition":
        cert = f", `@cert` {r.cert}" if r.cert else ""
        return f"{s['unclear']}× `<unclear>`, {s['supplied']}× `<supplied>`, {s['gap']}× `<gap>`{cert}"
    return f"proxy: {s['unclean']} editor-marked char(s) of {s['length']}"


def _c_formula(r: Reading) -> str:
    s = r.signals
    if s.get("kind") == "edition":
        if "k" in s:
            base = 1 - (0.5 * s["unclear"] + 0.7 * s["supplied"] + 1.0 * s["gap"]) / s["length"]
            return (f"(1 − (0.5·{s['unclear']} + 0.7·{s['supplied']} + 1.0·{s['gap']}) / {s['length']}) · "
                    f"k({r.cert}) = {max(0.0, base):.2f} · {s['k']} = **{r.confidence:.2f}**")
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
                     f"    rdf:subject    data:{str(subject_iri(stone, r.inscription)).rsplit('/', 1)[-1]} ;",
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
    add("A file that holds **several inscriptions** (Blackwaterfoot 1) is read per inscription: the "
        "readings of the first and of the second inscription are not alternatives of each other, so each "
        "inscription is its own subject (`ogham:Inscription`, linked from the stone by `ogham:hasInscription`) "
        "and its weights add up to 1 on their own. An apparatus reading is assigned to an inscription by the "
        "ordinal in the note of its `<app>` (\"For the second inscription, …\"). An inscription with no "
        "transliteration and no reading (the fourth one, in Blackwaterfoot 1) has no statement.\n")
    add("A `<rdg>` without `@source` has **no editor** in the file (the name stands in the note, not in an "
        "attribute). It is not attributed to anyone: the graph has no `prov:wasAttributedTo` for it.\n")
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

    add("**Rule v2** (written to `out/v2/`, next to v1) multiplies c of an edition that carries `@cert` by the "
        "GSAS degree of that level: `low` 0.6469, `medium` 0.8517, `high` 0.9690 (4-level layer of "
        "[GSAS](https://github.com/Research-Squirrel-Engineers/GSAS)); everything else is as in v1. The tables "
        "below are rule v1; the comparison is on the page *Stones* of the documentation.\n")
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
        "as `fw:TextEvidence` (`fw:derivedFrom`). Each reading whose source the file names is "
        "`prov:wasAttributedTo` its editor. "
        "The normalised weights are a belief distribution, bridged to CIDOC CRM's argumentation model "
        "**CRMinf (I2 Belief)**. Literal shape, taken from the data:\n")
    add("```turtle\n" + hextuple_example(results) + "\n```\n")
    add("**Axioms** (in `ontology/ogham-amt.ttl`, copied into every graph): `hasEditionReading` and "
        "`hasHistoricalReading` are kinds of `hasReading` (subsumption; the finer statement is written with "
        "the same weight next to the `hasReading` hextuple), and the chain `hasReading` then `attributedTo` gives "
        "`readByEditor` with product logic (the attribution has weight 1, so the weight of the reading carries "
        "over). The engine "
        "([`alpaca-fair-framework/amt-engine`](https://github.com/alpaca-fair-framework/amt-engine)) "
        f"derives `hasReading` and `readByEditor` from them; `{FUZZY_LOGIC}` is the logic of the chains. "
        "`python main.py --only reason` shows what it derives.\n")

    add("## 5. Per stone\n")
    for stone, readings, out in results:
        ident = stone_id(stone)
        n_ed = sum(1 for r in readings if r.is_edition)
        add(f"### {stone.get('title', '?')} ({stone_ref(stone)})\n")
        add(f"`{out}` — {len(readings)} reading(s): {n_ed} edition + {len(readings) - n_ed} historical.\n")
        for n, group in units(readings):
            if n is not None:
                add(f"#### Inscription {n}\n")
            add("| reading | editor | extracted doubt | c | a | amt:weight | type |")
            add("|---|---|---|---|---|---|---|")
            for r in sorted(group, key=lambda x: (-x.weight, x.source_id)):
                txt = r.text if len(r.text) <= 34 else r.text[:31] + "…"
                add(f"| {txt} | {r.editor} | {_signals_str(r)} | {r.confidence:.2f} | "
                    f"{r.agreement:.2f} | **{r.weight:.4f}** | {TYPE_TAG[reading_type(r)] or '-'} |")
            add("\n*c per reading:*\n")
            for r in sorted(group, key=lambda x: (-x.weight, x.source_id)):
                add(f"- {r.editor}: c = {_c_formula(r)}")
            subject = str(subject_iri(stone, n)).rsplit("/", 1)[-1]
            add(f"\n*AMT statements ({'inscription' if n is not None else 'stone'} → reading @ weight):*\n")
            for r in sorted(group, key=lambda x: (-x.weight, x.source_id)):
                add(f"- `{subject}` —`hasReading`→ *{r.editor}* · **weight {r.weight:.4f}**")
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


def process(input_path: Path, output_path: Path, shapes=None, ontology=None, rule: str = "v1"):
    stone, readings = analyse(input_path, rule)

    n_ed = sum(1 for r in readings if r.is_edition)
    if rule == "v1":
        print(f"\n{stone.get('title', '?')} ({stone_ref(stone)}) "
              f"-- {len(readings)} reading(s): {n_ed} edition + {len(readings) - n_ed} historical")
        for r in sorted(readings, key=lambda x: (-x.weight, x.source_id)):
            tag = "EDITION" if r.is_edition else "hist.  "
            part = "" if r.inscription is None else f"i{r.inscription} "
            print(f"  [{tag}] {part}{r.editor:22} c={r.confidence:.2f} a={r.agreement:.2f} "
                  f"w={r.weight:.4f} {TYPE_TAG[reading_type(r)]:>2}  {r.text[:46]}")

    g = build_graph(stone, readings, rule)
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
        print("\nRule v2 (@cert of the edition as a factor, GSAS degrees):")
        for f, b in STONES:
            process(DATA / f, OUT_V2 / f"{b}.amt.ttl", args.shapes, args.ontology, rule="v2")
        write_out_readme(results)
    if not (args.shapes and args.ontology):
        print("\n(SHACL skipped -- pass --shapes amt-shapes.ttl --ontology amt.ttl to validate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
