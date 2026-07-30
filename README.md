# Epidoc AMT - Ogham Prototype

Convert TEI/EpiDoc editions of ogham stones into **Academic Meta Tool (AMT)**
Turtle, so that competing scholarly readings become **weighted, reified
statements** that the [AMT reasoning engine](https://github.com/n4o-rse/amt-engine)
can process.

See **`out/README.md`** (generated) for the per-stone breakdown of extracted doubt, confidence scores and AMT modelling.

This is **axis 2 (vagueness modelling)** of the Linked Open Ogham crosswalk and
the companion of [`tei--epidoc-crosswalk`](https://github.com/LinkedOpenOgham/tei--epidoc-crosswalk)
(axis 1). It supports the DHd 2027 poster *"Mind the Gap zwischen Stein und
Graph"*.

## What it does

For each stone it collects the competing readings and emits an AMT graph:

- `amt:Concept` — the classes `OghamStone` and `Reading`
- `amt:Role` — the relation `hasReading`
- individuals — the stone and each reading, linked with `amt:instanceOf`
- weighted edges — one reified quadruple (`rdf:subject` / `rdf:predicate` /
  `rdf:object` + `amt:weight`) per reading
- provenance — each reading `prov:wasAttributedTo` its editor

A *reading* is either the **current edition** (the `<div type="edition">`
transliteration, attributed to the OG(H)AM editor) or a **historical**
alternative from the apparatus (`<rdg>`). Stones with a single reading and no
apparatus — the "clean" cases — yield exactly one edge with weight 1.0: the
method adds no doubt where the source shows none.

Four stones form a deliberate **spectrum of doubt**:

| Stone | CIIC | Readings | Epistemic profile |
|---|---|---|---|
| Gigha 1 | 506 | 5 (1 edition + 4 historical) | distributed weights — high uncertainty |
| Coomleagh East | 55 | 2 | two weighted alternatives |
| Garranes | 81 | 1 | single reading, weight 1.0 (minor restorations) |
| Ballinrannig 6 | 153 | 1 | single reading, weight 1.0 (no doubt markup) |

## Repository structure

```
tei--epidoc-amt/
├── data/                      # inputs (EpiDoc XML)
│   ├── S-ARL-001.xml          # Gigha 1 (CIIC 506)
│   ├── I-COR-001.xml          # Coomleagh East (CIIC 55)
│   ├── I-COR-030.xml          # Garranes (CIIC 81)
│   └── I-KER-020.xml          # Ballinrannig 6 (CIIC 153)
├── out/                       # generated outputs
│   ├── README.md              # extraction, scores, c, AMT modelling (generated)
│   └── *.amt.ttl              # one AMT graph per stone (generated)
├── py/
│   └── main.py                # single entry point:  python py/main.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation

Python 3.10+ and the libraries in `requirements.txt`:

```
pip install -r requirements.txt
```

`rdflib` builds the graph, `lxml` parses the EpiDoc XML, `pyshacl` is optional
(only for the validation step below).

## Usage

Run from the repository root:

```
python py/main.py
```

This processes all four stones in the `STONES` list and writes one
`out/<stone>.amt.ttl` per stone, plus `out/README.md`. Single-file mode and optional SHACL check:

```
python py/main.py --input data/S-ARL-001.xml --output out/gigha1.amt.ttl
python py/main.py --shapes amt-shapes.ttl --ontology amt.ttl   # validate all outputs
```

The two SHACL files ship with `n4o-rse/amt-engine`
(`ontology/amt-shapes.ttl`, `ontology/amt.ttl`).

## The weighting rule (v1)

Each reading *r* receives `amt:weight(r) ∈ [0, 1]` from two transparent factors:

1. **Reading confidence c(r)** — vagueness / precision.
   - *current edition*: from the markup, per-marker penalty
     `c = 1 − (0.5·#unclear + 0.7·#supplied + 1.0·#gap) / length` (clamped),
     mirroring per-character certainties (legible 1.0 / `<unclear>` 0.5 /
     `<supplied>` 0.3 / `<gap>` 0.0).
   - *historical `<rdg>`*: a proxy — the share of clean characters in the string.
2. **Tradition agreement a(r)** — uncertainty / belief across alternatives: the
   fraction of editors whose reading clusters with *r* (similarity ≥
   `AGREEMENT_THRESHOLD`).

```
raw(r)     = c(r) · a(r)
amt:weight = raw(r) / Σ raw(r)      # normalised over the alternatives, Σ = 1
```

The normalised weights form a belief distribution and are the natural bridge to
CIDOC CRM's argumentation model **CRMinf (I2 Belief)**. All constants live at the
top of `py/main.py`.

Example — Gigha 1 (edition + four historical readings):

| Reading | Editor | c | a | amt:weight |
|---|---|---|---|---|
| VICULA MAQ COMGINI | Macalister 1902 | 1.00 | 0.60 | 0.2727 |
| VICULA MAQ CUGINI | Macalister 1945 | 1.00 | 0.60 | 0.2727 |
| [---]MAQ[---]COGIN[---] | OG(H)AM edition | 0.50 | 0.80 | 0.1818 |
| MAQICAGILEB | Rhys 1899 | 1.00 | 0.40 | 0.1818 |
| OGMA MAQI TIGERNI | Rhys 1901 | 1.00 | 0.20 | 0.0909 |

## Note on the data

Gigha 1 records six historical readings, but two of them (Diack 1926, Jackson
1971) are **commented out** in the current EpiDoc file (pending a bibliographic
reference). The converter therefore processes the **four active** historical
readings plus the current edition; it will pick up the other two automatically
once the OG(H)AM team un-comments them.

## Context

Part of the **Linked Open Ogham** project. Ogham data from the CISP database and
the OG(H)AM TEI/EpiDoc editions is crosswalked to CIDOC CRM / CRMtex; this
repository adds the AMT vagueness layer on top of the competing readings.

## AI assistance

Parts of this repository were drafted with the assistance of Claude (Anthropic)
and reviewed by Florian Thiery.

## Author & licence

Florian Thiery. Code licensed under the **MIT License** (see `LICENSE`).

## TODO (to fill before publishing)

- Zenodo DOI and `CITATION.cff`
- Data licence / attribution for the EpiDoc input (OG(H)AM project)
- ORCID / affiliation
- Replace the c(r) proxy for historical readings with per-character certainty
