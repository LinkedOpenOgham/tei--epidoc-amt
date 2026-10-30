# Changelog

All notable changes to this repository. Dates are release dates. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
