"""Prose for the GitHub Pages documentation (British English).

Only words live here. Every table and every number is built by step_docs.py from
the ontology and from the data, so that the pages cannot drift from the model.
"""
from ogham_amt_utils import BLOB, GITHUB

STATUS = ("> **Status: prototype, release {release}.** The model is small on purpose. "
          "What is verified and what is still open is stated on the page [Run](run.html).")

INDEX_INTRO = """Ogham stones are read differently by different editors. This repository turns the
competing readings of four stones, as they stand in the OG(H)AM EpiDoc files, into **weighted statements** in
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

MODEL_NOTE = """The model has two concepts and one role. Nothing is inferred from it: the graphs hold weighted
statements only, no axioms. That is a deliberate choice for this release; the page [Run](run.html) says
what it means for the engine."""

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
| 3. Normalise | weight = c(r) * a(r) divided by the sum of c * a over all readings of the stone, rounded to four decimals. |
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
`run_amt.py <graph> --check-only --update` for each of the four graphs. `--check-only` validates against the
AMT shapes, loads the graph and runs the diagnostics (`AMT-E101`, `AMT-E102`, `AMT-E103`, `AMT-N301`), and
writes no output. The report is `build/check-report.txt`."""

RUN_REASONING = """The graphs contain **no axioms** (no role chains, inverses or subsumptions). A full run of the runner
therefore validates and exports, but infers nothing. Axioms are a modelling decision, not a technicality. The
proposals are in the PRIMER, steps S3 to S5."""

REVIEW_QUESTIONS = """## Questions for review

1. Is the confidence of a historical reading read from editor-marked characters (`[ ] ( ) ? / \\ - . :`) a fair
   proxy for reading confidence?
2. Is string similarity of 0.60 a sensible threshold for "the same reading"? Two editors who differ in one
   letter of eight read alike; two who differ in three do not.
3. Should a stone with a single, unmarked reading carry a type at all? Currently it carries none.
4. Should the weights of a stone be a share among alternatives (sum 1, as now), or independent degrees?"""

FOOTER_LINKS = {
    "repo": GITHUB,
    "ontology": BLOB + "ontology/ogham-amt.ttl",
    "convert": BLOB + "py/step_convert.py",
}
