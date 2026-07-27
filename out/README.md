# `out/` — extracted doubt and its AMT modelling

> **Generated file** — produced by `python py/main.py`. Do not edit by hand; it adapts to the EpiDoc inputs and to the weighting constants in `py/main.py`.

## 1. How doubt is extracted from an inscription

Each competing reading of a stone becomes one weighted edge. Two kinds of reading are read out of the EpiDoc file:

- the **current edition** — the `<div type="edition">` transliteration; and
- every active **historical reading** in the apparatus — `<rdg>` (readings commented out in the XML are ignored).

The editorial doubt markup is mapped to per-character base certainties:

| EpiDoc signal | meaning | base certainty | penalty (1 − certainty) |
|---|---|---|---|
| legible glyph | securely read | 1.0 | 0.0 |
| `<unclear>` | not clearly legible | 0.5 | 0.5 |
| `<supplied>` | editorially restored | 0.3 | 0.7 |
| `<gap>` | lost, not restored | 0.0 | 1.0 |

## 2. How the reading confidence c is computed

**Current edition** — from the markup counts (fuzzy-AND ≈ mean penalty over the string):

```
c = 1 − (0.5·#unclear + 0.7·#supplied + 1.0·#gap) / length
```

**Historical `<rdg>`** — usually no per-character markup, so a proxy from the editor-introduced doubt characters (brackets, slashes, dashes, `?`):

```
c = 1 − (editor-marked chars) / length
```

The **tradition agreement** `a` = fraction of editors whose reading clusters with r (string similarity ≥ 0.6). The edge weight is the normalised product

```
amt:weight(r) = c(r)·a(r) / Σ c·a          (Σ over the alternatives = 1)
```

## 3. How it is modelled with AMT

Every reading is an `amt:Concept` individual (`amt:instanceOf ogham:Reading`); the stone `hasReading` each of them as a **reified quadruple** carrying the `amt:weight`; each reading is `prov:wasAttributedTo` its editor. The normalised weights are a belief distribution, bridged to CIDOC CRM's argumentation model **CRMinf (I2 Belief)**. Literal shape:

```turtle
[] rdf:subject   data:stone_506 ;
   rdf:predicate ogham:hasReading ;
   rdf:object    data:reading_506_MAC1945 ;
   amt:weight    "0.2727"^^xsd:decimal .
```

The reasoning engine (`n4o-rse/amt-engine`) then combines these weights with the `amt:ProductLogic` operator when it applies inference axioms.

## 4. Per stone

### Gigha 1 (CIIC 506)

`gigha1.amt.ttl` — 5 reading(s): 1 edition + 4 historical.

| reading | editor | extracted doubt | c | a | amt:weight |
|---|---|---|---|---|---|
| VICULA MAQ COMGINI | Macalister 1902 | proxy: 0 editor-marked char(s) of 16 | 1.00 | 0.60 | **0.2727** |
| VICULA MAQ CUGINI | Macalister 1945 | proxy: 0 editor-marked char(s) of 15 | 1.00 | 0.60 | **0.2727** |
| [---]MAQ[---]COGIN[---] | OG(H)AM edition (KF) | 2× `<unclear>`, 0× `<supplied>`, 3× `<gap>` | 0.50 | 0.80 | **0.1818** |
| MAQICAGILEB | Rhys 1899 | proxy: 0 editor-marked char(s) of 11 | 1.00 | 0.40 | **0.1818** |
| OGMA MAQI TIGERNI | Rhys 1901 | proxy: 0 editor-marked char(s) of 15 | 1.00 | 0.20 | **0.0909** |

*c per reading:*

- Macalister 1902: c = 1 − 0 / 16 = **1.00**
- Macalister 1945: c = 1 − 0 / 15 = **1.00**
- OG(H)AM edition (KF): c = 1 − (0.5·2 + 0.7·0 + 1.0·3) / 8 = **0.50**
- Rhys 1899: c = 1 − 0 / 11 = **1.00**
- Rhys 1901: c = 1 − 0 / 15 = **1.00**

*AMT edges (stone → reading @ weight):*

- `stone_506` —`hasReading`→ *Macalister 1902* · **weight 0.2727**
- `stone_506` —`hasReading`→ *Macalister 1945* · **weight 0.2727**
- `stone_506` —`hasReading`→ *OG(H)AM edition (KF)* · **weight 0.1818**
- `stone_506` —`hasReading`→ *Rhys 1899* · **weight 0.1818**
- `stone_506` —`hasReading`→ *Rhys 1901* · **weight 0.0909**

### An Com Liath Thoir | Coomleagh East (CIIC 55)

`coomleagh-east.amt.ttl` — 2 reading(s): 1 edition + 1 historical.

| reading | editor | extracted doubt | c | a | amt:weight |
|---|---|---|---|---|---|
| ANM SAINA MAQ OGALA MUCOI TEMOCA | Macalister 1945 | proxy: 0 editor-marked char(s) of 27 | 1.00 | 0.50 | **0.6154** |
| .. ? ..TETA | OG(H)AM edition (NW) | 1× `<unclear>`, 0× `<supplied>`, 1× `<gap>` | 0.62 | 0.50 | **0.3846** |

*c per reading:*

- Macalister 1945: c = 1 − 0 / 27 = **1.00**
- OG(H)AM edition (NW): c = 1 − (0.5·1 + 0.7·0 + 1.0·1) / 4 = **0.62**

*AMT edges (stone → reading @ weight):*

- `stone_55` —`hasReading`→ *Macalister 1945* · **weight 0.6154**
- `stone_55` —`hasReading`→ *OG(H)AM edition (NW)* · **weight 0.3846**

### An Garrán | Garranes (CIIC 81)

`garranes.amt.ttl` — 1 reading(s): 1 edition + 0 historical.

| reading | editor | extracted doubt | c | a | amt:weight |
|---|---|---|---|---|---|
| CASSITTAS MAQI MUCOI CALLITI | OG(H)AM edition (NW) | 0× `<unclear>`, 3× `<supplied>`, 0× `<gap>` | 0.92 | 1.00 | **1.0000** |

*c per reading:*

- OG(H)AM edition (NW): c = 1 − (0.5·0 + 0.7·3 + 1.0·0) / 25 = **0.92**

*AMT edges (stone → reading @ weight):*

- `stone_81` —`hasReading`→ *OG(H)AM edition (NW)* · **weight 1.0000**

### Baile an Reannaigh | Ballinrannig 6 (CIIC 153)

`ballinrannig6.amt.ttl` — 1 reading(s): 1 edition + 0 historical.

| reading | editor | extracted doubt | c | a | amt:weight |
|---|---|---|---|---|---|
| CCICAMINIvac. MAQQ[/I] C[A]TTINI | OG(H)AM edition (NW) | 0× `<unclear>`, 0× `<supplied>`, 0× `<gap>` | 1.00 | 1.00 | **1.0000** |

*c per reading:*

- OG(H)AM edition (NW): c = 1 − (0.5·0 + 0.7·0 + 1.0·0) / 24 = **1.00**

*AMT edges (stone → reading @ weight):*

- `stone_153` —`hasReading`→ *OG(H)AM edition (NW)* · **weight 1.0000**

