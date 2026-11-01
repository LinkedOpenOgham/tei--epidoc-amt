# `out/` — extracted doubt and its AMT modelling

> **Generated file** — produced by `python main.py` (step `convert`). Do not edit by hand; it adapts to the EpiDoc inputs and to the weighting constants in `py/step_convert.py`.

## 1. How doubt is extracted from an inscription

Each competing reading of a stone becomes one weighted statement. Two kinds of reading are read out of the EpiDoc file:

- the **current edition** — the `<div type="edition">` transliteration; and
- every active **historical reading** in the apparatus — `<rdg>` (readings commented out in the XML are ignored).

A file that holds **several inscriptions** (Blackwaterfoot 1) is read per inscription: the readings of the first and of the second inscription are not alternatives of each other, so each inscription is its own subject (`ogham:Inscription`, linked from the stone by `ogham:hasInscription`) and its weights add up to 1 on their own. An apparatus reading is assigned to an inscription by the ordinal in the note of its `<app>` ("For the second inscription, …"). An inscription with no transliteration and no reading (the fourth one, in Blackwaterfoot 1) has no statement.

A `<rdg>` without `@source` has **no editor** in the file (the name stands in the note, not in an attribute). It is not attributed to anyone: the graph has no `prov:wasAttributedTo` for it.

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

The **tradition agreement** `a` = fraction of readings that cluster with r (string similarity ≥ 0.6). The weight is the normalised product

```
amt:weight(r) = c(r)·a(r) / Σ c·a          (Σ over the alternatives = 1)
```

**Rule v2** (written to `out/v2/`, next to v1) multiplies c of an edition that carries `@cert` by the GSAS degree of that level: `low` 0.6469, `medium` 0.8517, `high` 0.9690 (4-level layer of [GSAS](https://github.com/Research-Squirrel-Engineers/GSAS)); everything else is as in v1. The tables below are rule v1; the comparison is on the page *Stones* of the documentation.

## 3. How the FW type is set

The type names the factor that pulled the raw weight below 1. It does not change the weight.

| c < 1 (imprecise reading) | a < 1 (other readings disagree) | `fw:hasType` |
|---|---|---|
| no | no | none written; AMT reads a statement without type as `fw:Vagueness` |
| yes | no | `fw:Vagueness` |
| no | yes | `fw:Uncertainty` |
| yes | yes | `fw:FuzzinessWobbliness` |

## 4. How it is modelled with AMT

Every reading is an `amt:Concept` individual (`amt:instanceOf ogham:Reading`); the stone `hasReading` each of them as a **hextuple**: a reified statement (`rdf:subject`, `rdf:predicate`, `rdf:object`) carrying `amt:weight`, `fw:hasType` and `fw:hasMethod`, with the reading string as `fw:TextEvidence` (`fw:derivedFrom`). Each reading whose source the file names is `prov:wasAttributedTo` its editor. The normalised weights are a belief distribution, bridged to CIDOC CRM's argumentation model **CRMinf (I2 Belief)**. Literal shape, taken from the data:

```turtle
data:stmt_506_MAC1902
    rdf:subject    data:stone_506 ;
    rdf:predicate  ogham:hasReading ;
    rdf:object     data:reading_506_MAC1902 ;
    amt:weight     0.2727 ;
    fw:hasType     fw:Uncertainty ;
    fw:hasMethod   ogham:ConfidenceAgreementRule ;
    fw:derivedFrom data:evidence_506_MAC1902 .

data:evidence_506_MAC1902 a fw:TextEvidence ;
    fw:sourceString "VICULA MAQ COMGINI" .
```

**Axioms** (in `ontology/ogham-amt.ttl`, copied into every graph): `hasEditionReading` and `hasHistoricalReading` are kinds of `hasReading` (subsumption; the finer statement is written with the same weight next to the `hasReading` hextuple), and the chain `hasReading` then `attributedTo` gives `readByEditor` with product logic (the attribution has weight 1, so the weight of the reading carries over). The engine ([`alpaca-fair-framework/amt-engine`](https://github.com/alpaca-fair-framework/amt-engine)) derives `hasReading` and `readByEditor` from them; `amt:ProductLogic` is the logic of the chains. `python main.py --only reason` shows what it derives.

## 5. Per stone

### Gigha 1 (CIIC 506)

`gigha1.amt.ttl` — 5 reading(s): 1 edition + 4 historical.

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| VICULA MAQ COMGINI | Macalister 1902 | proxy: 0 editor-marked char(s) of 16 | 1.00 | 0.60 | **0.2727** | U |
| VICULA MAQ CUGINI | Macalister 1945 | proxy: 0 editor-marked char(s) of 15 | 1.00 | 0.60 | **0.2727** | U |
| [---]MAQ[---]COGIN[---] | OG(H)AM edition (KF) | 2× `<unclear>`, 0× `<supplied>`, 3× `<gap>`, `@cert` low | 0.50 | 0.80 | **0.1818** | FW |
| MAQICAGILEB | Rhys 1899 | proxy: 0 editor-marked char(s) of 11 | 1.00 | 0.40 | **0.1818** | U |
| OGMA MAQI TIGERNI | Rhys 1901 | proxy: 0 editor-marked char(s) of 15 | 1.00 | 0.20 | **0.0909** | U |

*c per reading:*

- Macalister 1902: c = 1 − 0 / 16 = **1.00**
- Macalister 1945: c = 1 − 0 / 15 = **1.00**
- OG(H)AM edition (KF): c = 1 − (0.5·2 + 0.7·0 + 1.0·3) / 8 = **0.50**
- Rhys 1899: c = 1 − 0 / 11 = **1.00**
- Rhys 1901: c = 1 − 0 / 15 = **1.00**

*AMT statements (stone → reading @ weight):*

- `stone_506` —`hasReading`→ *Macalister 1902* · **weight 0.2727**
- `stone_506` —`hasReading`→ *Macalister 1945* · **weight 0.2727**
- `stone_506` —`hasReading`→ *OG(H)AM edition (KF)* · **weight 0.1818**
- `stone_506` —`hasReading`→ *Rhys 1899* · **weight 0.1818**
- `stone_506` —`hasReading`→ *Rhys 1901* · **weight 0.0909**

### An Com Liath Thoir | Coomleagh East (CIIC 55)

`coomleagh-east.amt.ttl` — 2 reading(s): 1 edition + 1 historical.

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| ANM SAINA MAQ OGALA MUCOI TEMOCA | Macalister 1945 | proxy: 0 editor-marked char(s) of 27 | 1.00 | 0.50 | **0.6154** | U |
| .. ? ..TETA | OG(H)AM edition (NW) | 1× `<unclear>`, 0× `<supplied>`, 1× `<gap>` | 0.62 | 0.50 | **0.3846** | FW |

*c per reading:*

- Macalister 1945: c = 1 − 0 / 27 = **1.00**
- OG(H)AM edition (NW): c = 1 − (0.5·1 + 0.7·0 + 1.0·1) / 4 = **0.62**

*AMT statements (stone → reading @ weight):*

- `stone_55` —`hasReading`→ *Macalister 1945* · **weight 0.6154**
- `stone_55` —`hasReading`→ *OG(H)AM edition (NW)* · **weight 0.3846**

### An Garrán | Garranes (CIIC 81)

`garranes.amt.ttl` — 1 reading(s): 1 edition + 0 historical.

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| CASSITTAS MAQI MUCOI CALLITI | OG(H)AM edition (NW) | 0× `<unclear>`, 3× `<supplied>`, 0× `<gap>` | 0.92 | 1.00 | **1.0000** | V |

*c per reading:*

- OG(H)AM edition (NW): c = 1 − (0.5·0 + 0.7·3 + 1.0·0) / 25 = **0.92**

*AMT statements (stone → reading @ weight):*

- `stone_81` —`hasReading`→ *OG(H)AM edition (NW)* · **weight 1.0000**

### Baile an Reannaigh | Ballinrannig 6 (CIIC 153)

`ballinrannig6.amt.ttl` — 1 reading(s): 1 edition + 0 historical.

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| CCICAMINIvac. MAQQ[/I] C[A]TTINI | OG(H)AM edition (NW) | 0× `<unclear>`, 0× `<supplied>`, 0× `<gap>` | 1.00 | 1.00 | **1.0000** | - |

*c per reading:*

- OG(H)AM edition (NW): c = 1 − (0.5·0 + 0.7·0 + 1.0·0) / 24 = **1.00**

*AMT statements (stone → reading @ weight):*

- `stone_153` —`hasReading`→ *OG(H)AM edition (NW)* · **weight 1.0000**

### Dyke (S-MOR-001)

`dyke.amt.ttl` — 1 reading(s): 1 edition + 0 historical.

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| [---]RRMOQQDITTOSSS[---] [---]E… | OG(H)AM edition (LH) | 12× `<unclear>`, 0× `<supplied>`, 9× `<gap>`, `@cert` low | 0.68 | 1.00 | **1.0000** | V |

*c per reading:*

- OG(H)AM edition (LH): c = 1 − (0.5·12 + 0.7·0 + 1.0·9) / 47 = **0.68**

*AMT statements (stone → reading @ weight):*

- `stone_S_MOR_001` —`hasReading`→ *OG(H)AM edition (LH)* · **weight 1.0000**

### Blackwaterfoot 1 (S-BUT-001)

`blackwaterfoot-1.amt.ttl` — 8 reading(s): 2 edition + 6 historical.

#### Inscription 1

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| H(i/e)OMEQ(i/e)[~] | no editor named | proxy: 8 editor-marked char(s) of 18 | 0.56 | 0.50 | **0.3077** | FW |
| EOMEDTE or EOMEQE | no editor named | proxy: 0 editor-marked char(s) of 15 | 1.00 | 0.25 | **0.2769** | U |
| EVLEMOE or ENEMOE | no editor named | proxy: 0 editor-marked char(s) of 15 | 1.00 | 0.25 | **0.2769** | U |
| [---]MEQE[---] | OG(H)AM edition (KF) | 2× `<unclear>`, 0× `<supplied>`, 2× `<gap>` | 0.25 | 0.50 | **0.1385** | FW |

*c per reading:*

- no editor named: c = 1 − 8 / 18 = **0.56**
- no editor named: c = 1 − 0 / 15 = **1.00**
- no editor named: c = 1 − 0 / 15 = **1.00**
- OG(H)AM edition (KF): c = 1 − (0.5·2 + 0.7·0 + 1.0·2) / 4 = **0.25**

*AMT statements (inscription → reading @ weight):*

- `inscription_S_BUT_001_1` —`hasReading`→ *no editor named* · **weight 0.3077**
- `inscription_S_BUT_001_1` —`hasReading`→ *no editor named* · **weight 0.2769**
- `inscription_S_BUT_001_1` —`hasReading`→ *no editor named* · **weight 0.2769**
- `inscription_S_BUT_001_1` —`hasReading`→ *OG(H)AM edition (KF)* · **weight 0.1385**

#### Inscription 2

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| BLUEDLA | Forsyth 1996 | proxy: 0 editor-marked char(s) of 7 | 1.00 | 0.75 | **0.3913** | U |
| LUEDBH | Fis 2001 | proxy: 0 editor-marked char(s) of 6 | 1.00 | 0.50 | **0.2609** | U |
| [---]VUEDLA | OG(H)AM edition (KF) | 0× `<unclear>`, 0× `<supplied>`, 1× `<gap>` | 0.83 | 0.50 | **0.2174** | FW |
| ADLEUV | Forsyth 1996 | proxy: 0 editor-marked char(s) of 6 | 1.00 | 0.25 | **0.1304** | U |

*c per reading:*

- Forsyth 1996: c = 1 − 0 / 7 = **1.00**
- Fis 2001: c = 1 − 0 / 6 = **1.00**
- OG(H)AM edition (KF): c = 1 − (0.5·0 + 0.7·0 + 1.0·1) / 6 = **0.83**
- Forsyth 1996: c = 1 − 0 / 6 = **1.00**

*AMT statements (inscription → reading @ weight):*

- `inscription_S_BUT_001_2` —`hasReading`→ *Forsyth 1996* · **weight 0.3913**
- `inscription_S_BUT_001_2` —`hasReading`→ *Fis 2001* · **weight 0.2609**
- `inscription_S_BUT_001_2` —`hasReading`→ *OG(H)AM edition (KF)* · **weight 0.2174**
- `inscription_S_BUT_001_2` —`hasReading`→ *Forsyth 1996* · **weight 0.1304**

### Bishop Loch (S-LKS-X01)

`bishop-loch.amt.ttl` — 1 reading(s): 1 edition + 0 historical.

| reading | editor | extracted doubt | c | a | amt:weight | type |
|---|---|---|---|---|---|---|
| AT[---]H[---] AL | OG(H)AM edition (NW) | 0× `<unclear>`, 0× `<supplied>`, 2× `<gap>` | 0.60 | 1.00 | **1.0000** | V |

*c per reading:*

- OG(H)AM edition (NW): c = 1 − (0.5·0 + 0.7·0 + 1.0·2) / 5 = **0.60**

*AMT statements (stone → reading @ weight):*

- `stone_S_LKS_X01` —`hasReading`→ *OG(H)AM edition (NW)* · **weight 1.0000**

*Type: V = `fw:Vagueness`, U = `fw:Uncertainty`, FW = `fw:FuzzinessWobbliness`, `-` = no type written.*
