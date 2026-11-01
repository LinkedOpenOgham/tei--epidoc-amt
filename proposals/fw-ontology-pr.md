# Proposal for the FW ontology (PR to `caa-datadragons/FW_Ontology`)

**Status:** pull request opened: https://github.com/caa-datadragons/FW_Ontology/pull/3 . Prepared in release 0.7.0 of `tei--epidoc-amt`; the patch for the FW repository is delivered
separately (`fw-ontology-ogham-patch.zip`) and is applied there on a branch. This page records the decision and
the reasons, so that it is not lost when the PR is merged or changed.

## Principle

The FW ontology is general. Only what other projects can use goes into the PR. What belongs to the Ogham data
stays in the namespace `ogham:` of this repository: the roles `readByEditor` and `readingOf`, the axioms, the
concepts `Inscription` and `Editor`, and `ogham:recordStatus`.

## What the PR contains

1. **`fw:ProportionalShareRule`**, a new individual of `fw:RuleBasedMethod`. One unit of degree is shared among
   alternatives that compete for the same statement, in proportion to a score each has; the score is the product
   of factor scores. With equal scores the shares are equal, as in `fw:EqualShareRule`. The shares add up to 1,
   so a single alternative always gets 1. Our two rules are individuals of `fw:RuleBasedMethod` in `ogham:` and
   point to it with `skos:broadMatch`.
2. **Comment of `fw:hasType`:** the type is omitted when nothing lowers the degree; the absence of a type is not
   a type. This is what the hextuples of this repository do.
3. **Comment of `fw:RuleBasedMethod`:** the rule may act on the wording of the source, on its markup, or on both.
   Our rule reads the markup (`<unclear>`, `<supplied>`, `<gap>`) and the apparatus.
4. **A real example:** `data/fw_ogham_example.ttl` (the five readings of Gigha 1) and a section in `docs/amt.md`.

No class, property or domain is changed, and nothing is removed.

## What the PR leaves out, and why

- The rule that maps damage to `fw:Vagueness` and disagreement to `fw:Uncertainty` stays a comment in the example.
  It is a hypothesis of this project (PRIMER D2), not a recommendation for others.
- The roles and axioms for editors: they say something about readings and editors, not about fuzziness.
- The GSAS degrees for `@cert` (rule v2): they belong to GSAS; the FW ontology needs only the method.

## How to check the PR

`python main.py` in the FW repository builds the reference and the guide without error; `--strict` shows the same
three warnings as before (three `*ResourceValue` classes without comment), none new.

## Text for the pull request

**Title:** Add a proportional share rule and a real example from Linked Open Ogham

**Body:**

This adds one method individual, two clearer comments and a worked example. No class, property or domain changes.

- `fw:ProportionalShareRule` (a `fw:RuleBasedMethod`): shares one unit of degree among competing alternatives in
  proportion to the product of their factor scores. The equal share rule is the case where all scores are equal.
- `fw:hasType`: the comment says that the type is omitted when nothing lowers the degree.
- `fw:RuleBasedMethod`: the comment says that a rule may act on the wording of the source, on its markup, or on both.
- `data/fw_ogham_example.ttl` and a section in `docs/amt.md`: the five readings of an Ogham stone as hextuples, from
  https://github.com/LinkedOpenOgham/tei--epidoc-amt (release 0.6.0). The type rule in the comments is that project's
  hypothesis and is not part of the ontology.

The documentation builds (`python main.py`); `--strict` reports the same three warnings as before.
