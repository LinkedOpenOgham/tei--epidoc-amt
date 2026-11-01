# Changelog

All notable changes to this repository. Dates are release dates. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-11-01

Takes in the three stones of the CAA UK 2026 poster ("Purported, Alleged, Undetermined: Four Degrees of Doubt
in the Ogham Corpus"), with the same base names as `tei--epidoc-crosswalk`.

### Added
- Three stones in `data/` and `STONES`: Dyke (`S-MOR-001`), Blackwaterfoot 1 (`S-BUT-001`) and Bishop Loch
  (`S-LKS-X01`), with `out/dyke.amt.ttl`, `out/blackwaterfoot-1.amt.ttl` and `out/bishop-loch.amt.ttl`.
- Records with several inscriptions are read per inscription. New concept `ogham:Inscription` and plain link
  `ogham:hasInscription`; the weights of each inscription add up to 1 on their own. Only Blackwaterfoot 1 is
  affected (inscriptions 1 and 2; the third is commented out and the fourth has no text).
- Stone notes on the page "Stones" (Dyke, Blackwaterfoot 1, Bishop Loch), and two more limits of the weight on
  the page "Weights": the status of the object is not read (Bishop Loch), and `@cert` on the edition is not read
  (Dyke, Gigha 1).
- Tests: weights per inscription, inscriptions do not compete, no editor for a reading without source, IRIs of
  records without a CIIC number.

### Changed
- A record without a CIIC number is named by its file name (`data:stone_S_MOR_001`); `<idno type="CIIC"/>` with no
  text is no longer read as a number.
- A `<rdg>` without `@source` has no `prov:wasAttributedTo` (no shared agent for "unknown"). Its editor is shown as
  "no editor named". Four readings of Blackwaterfoot 1 are affected; the notes name the editor in prose only.
- `ogham:hasReading` has no formal domain any more: the subject is a stone, or an inscription in a record with
  several. Definition and scope note say so.
- The spectrum figure has one bar per stone, or per inscription. Prose counts follow `STONES`.
- `CITATION.cff`: ORCID and affiliation of the author.

### Unchanged
- Weighting rule v1 and every weight and type of the four earlier stones. Their graphs differ only in the
  ontology triples copied into every file (the new concept, the link, the reworded definitions). Figures 01 to 04
  have the same content.

## [0.2.1] - 2026-10-30

### Changed
- Diagrams: larger type relative to the page (the figures are drawn narrower, so the same point size reads
  larger when the page scales them).
- Docs, page "Weights": new section "What the weight does not say". The weights are shares among the
  readings of a stone; a single damaged reading carries weight 1, and the damage shows in the type. Review
  question 4 reworded accordingly.
- Decision recorded: weight rule v1 stays; no independent-degree rule (PRIMER, A4 and S4).

### Unchanged
- Every weight, every type, every graph. `out/` is byte-identical to 0.2.0; the build rewrites only `docs/`.

## [0.2.0] - 2026-10-30

Prepares the repository for AMT.engine 0.6.0 and adds documentation. The weights are unchanged.

### Added
- **Hextuple annotation.** Every weighted statement now carries `fw:hasType` (the factor that lowered
  the weight: `fw:Vagueness`, `fw:Uncertainty` or `fw:FuzzinessWobbliness`; none when nothing lowered it),
  `fw:hasMethod` and `fw:derivedFrom` (a `fw:TextEvidence` with the `fw:sourceString` of the reading).
- `ontology/ogham-amt.ttl`: the domain model (concepts `OghamStone`, `Reading`, role `hasReading`, method
  `ConfidenceAgreementRule`) as one source of truth, copied into every graph.
- GitHub Pages documentation in `docs/` (model, vocabulary, weights, stones, run) with five diagrams in the
  colours of the Linked Open Ogham logo.
- `main.py` as the single entry point, with `--list` and `--only`; steps `convert`, `diagrams`, `docs`,
  `tests`, and `check` (network, on request).
- `check`: runs the AMT runner with `--check-only` on every graph.
- `tests/test_convert.py`: weights sum to 1, hextuple complete, type rule, no blank nodes, determinism.
- `PRIMER.md` (work plan, German), `CITATION.cff`, this changelog.

### Changed
- The converter moved from `py/main.py` to `py/step_convert.py`. `python py/main.py` still works, with the
  same arguments.
- Statements are IRIs (`data:stmt_<CIIC>_<source>`), not blank nodes, so the Turtle is byte-identical between
  runs.
- `README.md`, `.gitignore`, `requirements.txt` (adds matplotlib).

### Unchanged
- The weighting rule v1 and every weight. The quadruples (stone, role, reading, weight) of the four graphs are
  identical to those of 0.1.0.

## [0.1.0]

First release: four stones converted to AMT graphs with weighted, reified statements.
