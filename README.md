# TEI/Epidoc AMT - Ogham Prototype

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

- `amt:Concept` — the classes `OghamStone`, `Reading`, `Editor` and (only for a record with several inscriptions) `Inscription`
- `amt:Role` — the relation `hasReading` (and its kinds, `attributedTo`, `readByEditor`)
- individuals — the stone and each reading, linked with `amt:instanceOf`
- weighted edges — one reified quadruple (`rdf:subject` / `rdf:predicate` /
  `rdf:object` + `amt:weight`) per reading
- provenance — each reading `prov:wasAttributedTo` its editor
- hextuple (since 0.2.0) — each weighted statement also names the **type** of
  doubt (`fw:hasType`), the **method** that produced the weight (`fw:hasMethod`)
  and the **evidence** it was derived from (`fw:derivedFrom`), as in
  AMT.engine 0.6.0

- axioms (since 0.5.0) — five, in `ontology/ogham-amt.ttl`: the sub-roles `hasEditionReading` and
  `hasHistoricalReading` of `hasReading`, and the chain `hasReading` then `attributedTo` gives
  `readByEditor` (product logic); the AMT engine derives the weight each editor carries for a stone
  (`python main.py --only reason`)
- record status (since 0.4.0) — `ogham:recordStatus` on the stone: `numbered`,
  `lost` or `doubtful`, read from the series letter of the identifier, as in the crosswalk
- two rules (since 0.4.0) — `out/*.amt.ttl` follows rule v1; `out/v2/*.amt.ttl`
  follows rule v2, which multiplies c of an edition that carries `@cert` by the
  [GSAS](https://github.com/Research-Squirrel-Engineers/GSAS) degree of that level
  (low 0.6469, medium 0.8517, high 0.9690)

A *reading* is either the **current edition** (the `<div type="edition">`
transliteration, attributed to the OG(H)AM editor) or a **historical**
alternative from the apparatus (`<rdg>`). Stones with a single reading and no
apparatus — the "clean" cases — yield exactly one edge with weight 1.0: the
method adds no doubt where the source shows none.

Seven stones form a deliberate **spectrum of doubt**:

| Stone | CIIC | Readings | Epistemic profile |
|---|---|---|---|
| Gigha 1 | 506 | 5 (1 edition + 4 historical) | distributed weights — high uncertainty |
| Coomleagh East | 55 | 2 | two weighted alternatives |
| Garranes | 81 | 1 | single reading, weight 1.0 (minor restorations) |
| Ballinrannig 6 | 153 | 1 | single reading, weight 1.0 (no doubt markup) |
| Dyke | – (`S-MOR-001`) | 1 | single reading, weight 1.0; the edition is marked `cert="low"`, which the rule does not read |
| Blackwaterfoot 1 | – (`S-BUT-001`) | 4 + 4, per inscription | two inscriptions, each weighted on its own; three readings have no named editor |
| Bishop Loch | – (`S-LKS-X01`) | 1 | single reading, weight 1.0; the doubt about the object is in prose only (the limit of the method) |

A record without a CIIC number is named by its file name. A file that holds
several inscriptions is read per inscription: readings of different
inscriptions are not alternatives of each other, so each inscription is its own
subject (`ogham:Inscription`, linked from the stone by `ogham:hasInscription`)
and its weights add up to 1 on their own. A `<rdg>` without `@source` is not
attributed to anyone.

## Repository structure

```
tei--epidoc-amt/
├── data/                      # inputs (EpiDoc XML), unchanged
├── ontology/
│   └── ogham-amt.ttl          # the domain model: 4 concepts, 8 roles, 1 link, 2 methods, 5 axioms
├── out/                       # generated outputs
│   ├── README.md              # extraction, scores, c, AMT modelling (generated)
│   ├── *.amt.ttl              # one AMT graph per stone, rule v1 (generated)
│   └── v2/*.amt.ttl           # the same under rule v2 (generated)
├── proposals/                 # the proposal for the FW ontology (pull request text)
├── feedback/                  # a note for the OG(H)AM team (drafts, not sent)
├── docs/                      # GitHub Pages: model, vocabulary, weights, stones, run
│   ├── _config.yml, _layouts/, assets/    # Jekyll shell and logo (sources)
│   └── *.md, diagrams/        # generated
├── py/
│   ├── step_convert.py        # EpiDoc -> AMT Turtle
│   ├── step_diagrams.py       # five figures in the colours of the project logo
│   ├── step_docs.py           # the documentation pages
│   ├── step_tests.py, step_check.py
│   ├── ogham_amt_utils.py     # release, paths, namespaces
│   └── main.py                # compatibility entry point (calls step_convert)
├── tests/test_convert.py
├── main.py                    # the single entry point:  python main.py
├── PRIMER.md                  # work plan (German)
├── CHANGELOG.md, CITATION.cff, LICENSE
├── .gitignore
├── README.md
└── requirements.txt
```

## Installation

Python 3.10+ and the libraries in `requirements.txt`:

```
pip install -r requirements.txt
```

`rdflib` builds the graph, `lxml` parses the EpiDoc XML, `matplotlib` draws the
diagrams, `pyshacl` is optional (only for the SHACL option below).

## Usage

Run from the repository root:

```
python main.py
```

This converts the seven stones (`out/<stone>.amt.ttl`, `out/v2/<stone>.amt.ttl` and `out/README.md`), draws
the diagrams, writes the documentation into `docs/` and runs the tests. The
build has no clock in it: a second run changes no file.

```
python main.py --list
python main.py --only convert
python main.py --only check
python main.py --only reason
```

`--only check` and `--only reason` are the steps that need the network. They fetch the
[amt-runner](https://github.com/alpaca-fair-framework/amt-runner), which in turn
fetches the AMT engine. `check` runs `--check-only` on every graph of `out/` and `out/v2/`:
validation against the AMT shapes, loading, diagnostics. `reason` lets the engine reason over the
graphs and lists the edges it derives (`build/reason-report.txt`). Nothing is written outside `build/`.

The earlier entry point still works:

```
python py/main.py --input data/S-ARL-001.xml --output out/gigha1.amt.ttl
python py/main.py --shapes amt-shapes.ttl --ontology amt.ttl   # validate all outputs
```

The two SHACL files ship with the AMT engine
([`alpaca-fair-framework/amt-engine`](https://github.com/alpaca-fair-framework/amt-engine),
`ontology/amt-shapes.ttl`, `ontology/amt.ttl`).

## Documentation

The pages in `docs/` (model, vocabulary, weights, every reading of the seven
stones, how to run the check) are served by GitHub Pages when *Settings, Pages*
points at the `/docs` folder of the main branch. They are written by
`python main.py --only docs` from the ontology and the data.

## The hextuple annotation

One weighted statement, as written to `out/gigha1.amt.ttl`:

```turtle
data:stmt_506_MAC1945
    rdf:subject    data:stone_506 ;
    rdf:predicate  ogham:hasReading ;
    rdf:object     data:reading_506_MAC1945 ;
    amt:weight     0.2727 ;
    fw:hasType     fw:Uncertainty ;
    fw:hasMethod   ogham:ConfidenceAgreementRule ;
    fw:derivedFrom data:evidence_506_MAC1945 .
```

The type says which factor lowered the weight: c < 1 gives `fw:Vagueness`, a < 1
gives `fw:Uncertainty`, both give `fw:FuzzinessWobbliness`, neither writes no
type. The quadruple core is unchanged against release 0.1.0, so existing
consumers read the same weights. Statements are IRIs, not blank nodes, so the
Turtle is deterministic.

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
top of `py/step_convert.py`.

Example — Gigha 1 (edition + four historical readings):

| Reading | Editor | c | a | amt:weight |
|---|---|---|---|---|
| VICULA MAQ COMGINI | Macalister 1902 | 1.00 | 0.60 | 0.2727 |
| VICULA MAQ CUGINI | Macalister 1945 | 1.00 | 0.60 | 0.2727 |
| [---]MAQ[---]COGIN[---] | OG(H)AM edition | 0.50 | 0.80 | 0.1818 |
| MAQICAGILEB | Rhys 1899 | 1.00 | 0.40 | 0.1818 |
| OGMA MAQI TIGERNI | Rhys 1901 | 1.00 | 0.20 | 0.0909 |

**Reading the weights.** The weights of a stone are shares among its readings
and add up to 1. A stone with a single reading therefore always has weight 1,
even if that reading is damaged (Garranes, c = 0.92); the damage shows in the
type (`fw:Vagueness`), not in the number.

## Note on the data

Gigha 1 records six historical readings, but two of them (Diack 1926, Jackson
1971) are **commented out** in the current EpiDoc file (pending a bibliographic
reference). The converter therefore processes the **four active** historical
readings plus the current edition; it will pick up the other two automatically
once the OG(H)AM team un-comments them.

## Data licence

The OG(H)AM editions in `data/` declare **CC BY 4.0** in their `<licence>` element
(teiHeader). The code in this repository is MIT (`LICENSE`). The Linked Open Ogham logo in `docs/assets/` is
the author's own work and licensed **CC BY 4.0**.

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

- Zenodo DOI (`CITATION.cff` is in place; add the DOI after the first release; release 0.7.1 is tagged only)
- Open: the c(r) of historical readings stays a proxy, because the data hold no per-character certainty
  (PRIMER, S5, closed)
