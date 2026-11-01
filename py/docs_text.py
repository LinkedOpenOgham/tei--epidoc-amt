"""Prose for the GitHub Pages documentation (British English).

Only words live here. Every table and every number is built by step_docs.py from
the ontology and from the data, so that the pages cannot drift from the model.
"""
from ogham_amt_utils import BLOB, GITHUB

STATUS = ("> **Status: prototype, release {release}.** The model is small on purpose. "
          "What is verified and what is still open is stated on the page [Run](run.html).")

INDEX_INTRO = """Ogham stones are read differently by different editors. This repository turns the
competing readings of {stones} stones, as they stand in the OG(H)AM EpiDoc files, into **weighted statements** in
the vocabulary of the [Academic Meta Tool (AMT)](https://github.com/alpaca-fair-framework/amt-engine). Doubt
is not removed and not hidden in a footnote: every reading becomes one statement, and the weights of the
readings of one stone add up to 1."""

IDEA = """1. **One statement per reading.** The stone is linked to each reading by the role `hasReading`; the
   statement carries a weight.
2. **The weight is computed, not typed.** Reading confidence (from the doubt markup) times tradition
   agreement (how many editors read it alike), normalised per stone.
3. **The kind of doubt is named.** Each statement says whether the weight was lowered by vagueness,
   by uncertainty or by both, using the three types of the
   [Fuzziness-Wobbliness ontology](https://github.com/alpaca-fair-framework/FW_Ontology)."""

MODEL_NOTE = """The model has four concepts (stone, inscription, reading, editor), eight roles and one plain link
(`hasInscription`, written only for records with several inscriptions). Five axioms say what the engine can
derive from the weighted statements: an edition reading and a historical reading are readings (subsumption), and
a stone, or its inscription, is read by the editor of its reading (role chain, with product logic). The page
[Run](run.html) says what the engine then does."""

AXIOM_INTRO = """The axioms are written in `ontology/ogham-amt.ttl` and copied into every graph, so that the AMT
engine finds them next to the data. They are proposals, to be reviewed (PRIMER S3). The graphs assert the finer
statement (`hasEditionReading` or `hasHistoricalReading`) with the same weight next to the `hasReading`
statement, so that a consumer without the role hierarchy still finds every `hasReading` edge. `readByEditor` is never
asserted: it appears only when the engine reasons."""

HEXTUPLE_INTRO = """AMT stores a weighted statement as a reified triple plus the weight. Release {release} adds the
three annotations of the hextuple of AMT.engine 0.6.0: the type of the doubt, the method that produced the
weight, and the evidence it was derived from. The quadruple core (subject, predicate, object, weight) is
unchanged; the committed Turtle of release 0.1 and the new Turtle agree on every quadruple."""

WEIGHT_INTRO = """The rule is the one of the first release (rule v1). It is unchanged; this release only makes
visible which factor lowered a weight."""

WEIGHT_STEPS = """| Step | What happens |
|---|---|
| 1. Reading confidence c(r) | For the current edition from the markup: `unclear`, `supplied` and `gap` lower it. For a historical reading, from the characters the editor marked as doubtful. A reading without any marker has c = 1. |
| 2. Tradition agreement a(r) | The share of the readings of the stone that cluster with this one, by string similarity of at least 0.60. |
| 3. Normalise | weight = c(r) * a(r) divided by the sum of c * a over all readings of the same stone, or of the same inscription where a file holds several, rounded to four decimals. |
| 4. Type | c < 1 and a = 1: fw:Vagueness. a < 1 and c = 1: fw:Uncertainty. Both below 1: fw:FuzzinessWobbliness. Neither: no type is written, and AMT.engine reads the default fw:Vagueness. |"""

TYPE_NOTE = """> The typing follows the Fuzziness-Wobbliness ontology: **vagueness** is a degree to which a
> reading is legible, **uncertainty** is doubt between alternatives. Whether a given marker belongs under one or the
> other is a scholarly decision. It is recorded in `py/step_convert.py` (`reading_type`) and is open for review
> (see the PRIMER, point D)."""

RUN_INTRO = """The graphs in `out/` are written for the AMT runner. This page says what has been checked and how
to run the check yourself."""

RUN_CHECK = """The check needs network access, because the runner fetches the engine from GitHub. It is therefore its own
step and is not part of the default build:

```
python main.py --only check
```

It clones the [amt-runner]({runner}) into `build/` (ignored by git), then calls
`run_amt.py <graph> --check-only --update` for each of the {graphs} graphs. `--check-only` validates against the
AMT shapes, loads the graph and runs the diagnostics (`AMT-E101`, `AMT-E102`, `AMT-E103`, `AMT-N301`), and
writes no output. The report is `build/check-report.txt`."""

RUN_REASONING = """The graphs contain five axioms (two subsumptions, two role chains, one disjointness). A full run of the
engine therefore derives `readByEditor` (or `inscriptionReadByEditor`): how much weight the readings of one editor
carry for the stone. For Gigha 1 it derives five edges: Macalister 1902 and 1945 0.2727 each, the OG(H)AM
edition (KF) and Rhys 1899 0.1818 each, Rhys 1901 0.0909; each is the weight of the reading of that editor. An
editor with two readings of one inscription keeps the larger weight (Forsyth 1996 on the second inscription of
Blackwaterfoot 1: 0.3913). The subsumptions derive nothing new, because the `hasReading` edges are asserted too;
they document the hierarchy for the engine. The disjointness axiom is checked by the engine's consistency check.

```
python main.py --only reason
```

writes the reasoned graphs and reports into `build/reasoned/` (network; not part of the default build)."""

SHARE_NOTE = """## What the weight does not say

The weights of a stone are **shares among the readings of that stone**, not independent degrees of belief.
They add up to 1 by construction. Two consequences follow, and both are intended:

- A stone with one reading always carries weight 1, even when that reading is damaged. Garranes
  (c = 0.92) and Ballinrannig 6 (c = 1.00) both have weight 1.0000. The weight of a single reading says
  "this is the only reading on record", not "this reading is certain".
- The damage is not lost: it is in the type. Garranes carries `fw:Vagueness`, Ballinrannig 6 carries none.
  The factors c(r) and a(r) are shown on the page [Stones](stones.html) and in `out/README.md`.

An independent degree for a single reading would need a different rule. That is not part of this release;
the decision and its reason are recorded in the PRIMER (A4, 2026-10-30).

Two more things the weight does not say, both visible in the stones of release 0.3.0:

- **It reads the markup of the reading, not the status of the object.** Bishop Loch carries one reading
  with two `<gap>` elements, so its weight is 1.0000 and its type `fw:Vagueness`. Whether the object is an
  ogham inscription at all is said only in prose in the record (see [Stones](stones.html)); no element
  carries it, so no weight can.
- **Rule v1 does not read `@cert` on the edition.** The edition of Gigha 1 and of Dyke carries `cert="low"`
  on its `<div>`. Rule v1 counts `unclear`, `supplied` and `gap` and ignores the attribute, so the
  doubt the editors put on the whole edition is not in c(r). Rule v2 reads it (next section).

## Rule v2: the certainty of the edition

Rule v2 is rule v1 with one more factor: the `@cert` of the edition multiplies c(r) by k. The values of k are
the degrees of the 4-level layer of [GSAS](https://github.com/Research-Squirrel-Engineers/GSAS) (Gradual
Semantic Alignment for SKOS, commit `bdbe0fb`, `skos_4level/skos_4level_degrees.csv`), rounded to four
decimals, and the TEI levels map to them one to one:

| `@cert` | GSAS level | k |
|---|---|---|
| `low` | `skosplus:relatedMatchLow` | 0.6469 |
| `medium` | `skosplus:relatedMatchMedium` | 0.8517 |
| `high` | `skosplus:relatedMatchHigh` | 0.9690 |
| none | | 1 |

The apparatus readings have no `@cert`, so k = 1 for them. v2 is written next to v1, not instead of it:
`out/*.amt.ttl` is v1 (`ogham:ConfidenceAgreementRule`), `out/v2/*.amt.ttl` is v2
(`ogham:ConfidenceCertAgreementRule`). The mapping of the TEI levels to the GSAS levels, and the use of a
product, are proposals to be reviewed. A stone with one reading keeps weight 1 under v2 as well, because the
weights are shares: v2 changes only the weights of a stone whose readings compete. Of the seven stones, that is
Gigha 1 (the edition carries `cert="low"`); the comparison is on the page [Stones](stones.html)."""

REVIEW_QUESTIONS = """## Questions for review

1. Is the confidence of a historical reading read from editor-marked characters (`[ ] ( ) ? / \\ - . :`) a fair
   proxy for reading confidence?
2. Is string similarity of 0.60 a sensible threshold for "the same reading"? Two editors who differ in one
   letter of eight read alike; two who differ in three do not.
3. Should a stone with a single, unmarked reading carry a type at all? Currently it carries none.
4. The weights are shares among alternatives (sum 1). Is that the right reading of "weight" for a single,
   damaged reading, given that the damage then shows in the type and not in the number? (See
   [Weights](weights.html).)"""

# Notes per stone on the page "Stones", keyed by the output base name. Each sentence is taken from the
# EpiDoc record or from the converter; nothing is added about the objects.
STONE_NOTES = {
    "dyke": """The record has no CIIC number; its file name `S-MOR-001` names it. The note in the apparatus speaks
of three inscriptions, but the file holds one transliteration of three lines, which is one reading here.
The edition carries `cert="low"` on its `<div>`: rule v1 does not read it, rule v2 does (see [Weights](weights.html)); the
weight stays 1.0000 under both, because there is no other reading to share it with.""",
    "blackwaterfoot-1": """The file holds several inscriptions, and the notes of the apparatus say which reading belongs to
which ("For the second inscription, ..."). Each inscription with a reading is its own subject
(`ogham:Inscription`, linked by `ogham:hasInscription`), and its weights add up to 1 on their own: the
readings of the first inscription are not alternatives of the second. The third inscription is commented
out in the file and the fourth has no text and no reading, so neither has a statement.

Four of the apparatus readings have no `@source`; the note names the editor in prose (for example Jackson
1973), but the graph does not parse prose, so these readings have no `prov:wasAttributedTo`. The two readings
of `FOR1996` on the second inscription are two nodes in this graph.""",
    "bishop-loch": """The record has no CIIC number; its identifier carries the series letter X, which the sister
repository [tei--epidoc-crosswalk](https://github.com/LinkedOpenOgham/tei--epidoc-crosswalk) exports as
`ogham:recordStatus "doubtful"`; so does this graph. The record calls the markings "purported" and
"alleged" and the object a stick "bearing ogham-like markings", in prose only. The only
markup in the edition is two `<gap>` elements. That is the **limit of the method**: the single reading has
weight 1.0000 and type `fw:Vagueness` (c = 0.60 from the gaps), and neither says that the object may not
carry an ogham inscription. The doubt about the object is not in the markup, so it cannot be in the weight.""",
}

FOOTER_LINKS = {
    "repo": GITHUB,
    "ontology": BLOB + "ontology/ogham-amt.ttl",
    "convert": BLOB + "py/step_convert.py",
}
