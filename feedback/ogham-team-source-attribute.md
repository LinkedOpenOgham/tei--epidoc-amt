# Suggestion for the OG(H)AM team: `@source` on three readings of Blackwaterfoot 1

**To:** the maintainers of the OG(H)AM EpiDoc files (`lguariento/og-h-am`)
**From:** Florian Thiery (LEIZA), for the project Linked Open Ogham
**Status:** draft, not sent. Delivered with release 0.7.0 of `tei--epidoc-amt`.
**Language:** English, so that it can be copied into an issue.

## What this is about

The Linked Open Ogham repositories read your EpiDoc files. `tei--epidoc-amt` weights the readings of a stone
(the edition and the readings of the apparatus) and records, for every reading, who proposed it. It takes the
editor from the `@source` attribute of `<rdg>`. A `<rdg>` without `@source` therefore has no editor in our
graph, even if the note next to it names one.

## The three readings

In `S-BUT-001.xml` (Blackwaterfoot 1), the following `<rdg>` have no `@source`. The `<note>` of the same `<app>`
names the editor in prose:

| `<app n>` | `<rdg>` | The note says | Suggested attribute |
|---|---|---|---|
| 2 | `EOMEDTE or EOMEQE` | "Jackson (1973, 53) read:" | `source="JAC1973"` |
| 3 | `EVLEMOE or ENEMOE` | "Jackson (1973, 53) also read:" | `source="JAC1973"` |
| 4 | `H(i/e)OMEQ(i/e)[~]` | "Forsyth (1996, 96) proposed the following reading:" | `source="FOR1996"` |

The `<bibl>` list of the same file already has `JAC1973` and `FOR1996`, and the other readings of the apparatus
(`<app n>` 5 to 7) already carry `@source`. The change would make the apparatus uniform. It would also make the
three readings count for their editors in our graph.

## What would change on our side

Nothing in the code. The three readings would get an agent (`Jackson 1973`, `Forsyth 1996`), and the weight of
every reading stays as it is, because the weights are shares of the readings of one inscription and do not
depend on who proposed a reading.

## Other points we noticed (optional)

- The edition `<div type="edition" subtype="ogham">` has `source="JAC1973"` and `resp="XS"`, while the choices
  inside it use `resp="KF"`. We read the editor of the edition from `@resp`. Does `@source` on the edition mean
  that the reading follows Jackson 1973? If so, we would like to record that.
- `<licence>` reads "Internantional" (sic) in the header of this file.

## How to check

`python main.py` in `tei--epidoc-amt` prints one line per reading. A reading without an editor is shown as
"no editor named". After your change, the three lines show the editor.
