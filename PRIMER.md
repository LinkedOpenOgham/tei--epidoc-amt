# PRIMER: tei--epidoc-amt

Arbeitsplan für das Repository `LinkedOpenOgham/tei--epidoc-amt`. Wird zu Beginn jedes Chats hochgeladen und am Ende zurückgeschrieben. Alles Nach-außen-Sichtbare (Code, README, Ontologie, Docs) ist britisches Englisch, dieses Dokument ist deutsch.

Stand: 2026-11-01, Release 0.3.0.

---

# Teil A: Immer gültig

## A1 Ausgangslage

| Repo | Rolle | Stand |
|---|---|---|
| `LinkedOpenOgham/tei--epidoc-amt` | dieses Repo: OG(H)AM-EpiDoc, sieben Steine, AMT-Graphen | 0.3.0 |
| `LinkedOpenOgham/tei--epidoc-crosswalk` | Achse 1 (CIDOC CRM), gleiche sieben Basisnamen, `ogham:recordStatus` und Zweifelsprofil am Stein | 0.2.2, nicht angefasst |
| `alpaca-fair-framework/amt-engine` (früher `n4o-rse/`) | AMT.engine, hier gegen 0.6.0 modelliert | nicht angefasst |
| `alpaca-fair-framework/amt-runner` (früher `n4o-rse/`) | Wrapper, klont die Engine, `--check-only` | 0.5.0, nicht angefasst |
| `alpaca-fair-framework/FW_Ontology` | Fuzziness-Wobbliness-Ontologie (fw:Vagueness, fw:Uncertainty, …) | nur gelesen |
| `LinkedOpenOgham/logo` | Logo und Farben für die Docs | nur Logo-SVG kopiert |
| `leiza-scit/CHNT2026-amt` | Vorlage für Docs-Stil und Diagramm-Kit | nur gelesen |

Nicht neu bauen: die Gewichtungsregel v1 (Gewichte der vier alten Steine identisch zu 0.1.0, geprüft; in 0.3.0 erneut), die EpiDoc-Dateien in `data/` (die drei neuen sind Kopien der Blobs aus `og-h-am`, Stand `9a68afd`, identisch zu `bb62ccd`).

**Befunde** (geprüft 2026-10-30):

- AMT wird im Repo **nur als Datenmodell** benutzt: zwei Konzepte (`OghamStone`, `Reading`), eine Rolle (`hasReading`), gewichtete reifizierte Aussagen. **Keine Axiome** (keine Rollenketten, Inversen, Subsumtionen), die Engine wird im Repo nicht aufgerufen. Ein Reasoning-Lauf validiert und exportiert daher nur, er schließt nichts.
- Die Aussagen waren in 0.1.0 Blank Nodes. Das Turtle war deshalb nicht byte-stabil. Seit 0.2.0 sind es IRIs (`data:stmt_<CIIC>_<Quelle>`).
- Engine 0.6.0 kennt das Hextupel: `fw:hasType` (Vagueness, Uncertainty, FuzzinessWobbliness, Default Vagueness), `fw:hasMethod`, `fw:derivedFrom` (`fw:TextEvidence` mit `fw:sourceString`). `fw:hasDegreeOfConnection` entspricht `amt:weight`. 0.1.0 trug nichts davon.
- Die Gewichtsformel `c·a / Σ(c·a)` war nirgends als Methode benannt. Die FW-Ontologie hat `fw:EqualShareRule` (für die Samian-Daten), aber keine passende Regel. Daher `ogham:ConfidenceAgreementRule` im Repo.
- **Normalisierung versteckt c.** Garranes hat eine einzige Lesung mit c = 0,92, ihr Gewicht ist trotzdem 1,0000. Der Typ (fw:Vagueness) zeigt das jetzt an, das Gewicht allein nicht. Beschlossen 2026-10-30: bleibt so (A4), die Docs erklären es auf der Seite Weights.
- Gigha 1: sechs historische Lesungen, zwei (Diack 1926, Jackson 1971) sind in der EpiDoc-Datei auskommentiert. Der Konverter verarbeitet vier. Das ist in der README vermerkt.
- **Nicht geprüft:** ob die Engine/der Runner die Graphen akzeptiert. Der Lauf `--check-only` wurde im Entstehungs-Chat nicht ausgeführt (Ausführung von geklontem Code wurde von der Sandbox verweigert). Stattdessen wurden die SHACL-Shapes der Engine mit pyshacl gegen die Graphen geprüft: konform. Das ersetzt S2 nicht.

## A2 Zielbild

```
data/*.xml (EpiDoc)
   |  py/step_convert.py   (Regel v1: c, a, Gewicht, Typ)
   v
out/*.amt.ttl  ---- python main.py --only check ---->  AMT-Runner / Engine 0.6.0
   |                                                     (Validierung, Diagnose, später Reasoning)
   |  py/step_diagrams.py, py/step_docs.py
   v
docs/  (GitHub Pages, Logo-Farben)       out/README.md
```

Eigenschaften, die das Ergebnis haben muss:

1. Die Gewichte eines Steins, bei mehreren Inschriften je Inschrift, summieren sich auf 1 (Toleranz 0,0005). Test.
2. Jede Aussage hat genau ein Gewicht, eine Methode, eine Evidenz und höchstens einen Typ. Test.
3. Zwei Läufe hintereinander ändern keine Datei (auch nicht SVG/PNG). `git status` bleibt sauber.
4. Die Quadrupel (Stein, Rolle, Lesung, Gewicht) sind identisch zum Stand vor der Hextupel-Erweiterung. Einmalig geprüft für 0.2.0.
5. `python main.py --only check` meldet für alle sieben Graphen keinen Befund (offen, S2).

## A3 Querschnittsregeln

- `data/` ist Eingabe, unverändert. Alles, was ein Skript daraus macht, liegt in `out/` oder `docs/`.
- **Keine Uhr in der Ausgabe.** Kein `datetime.now()`. Das Datum kommt aus der Konstante `RELEASE` oder aus den Daten.
- **Zweimal laufen lassen, `git status` bleibt sauber.** Blank Nodes sind verboten (Skolem-IRIs).
- Netzwerk nur im eigenen Schritt: `python main.py --only check`. Der Standardlauf ist offline.
- Die Ontologie `ontology/ogham-amt.ttl` ist die einzige Quelle für Konzepte, Rolle und Methode. Konverter und Docs lesen sie, nichts steht doppelt im Code.
- Typregel: c < 1 → Vagueness, a < 1 → Uncertainty, beides → FuzzinessWobbliness, keines → kein Typ.
- Britisches Englisch außen, Deutsch hier. Befehle für Windows `cmd`, je eine Zeile.
- Änderungen kommen als Patch-ZIP (Skill `patch-zip-delivery`), nur Quellen, gegen eine frische Kopie des Originals geprüft.

## A4 Beschlusslage

| Frage | Beschluss | seit |
|---|---|---|
| Wie werden Zweifelstypen modelliert? | `fw:hasType` pro Aussage, nach Faktor: c < 1 Vagueness, a < 1 Uncertainty, beides FuzzinessWobbliness | Vorschlag 2026-10-30 |
| Methode der Gewichtsregel | eigenes Individuum `ogham:ConfidenceAgreementRule a fw:RuleBasedMethod`, später in die FW-Ontologie übernehmen (S6) | Vorschlag 2026-10-30 |
| Aussagen-IRIs | `http://data.ogham.link/amt/stmt_<CIIC>_<Quelle>`, Konflikte mit Suffix `_2` | Vorschlag 2026-10-30 |
| Namensräume | Domäne `http://ontology.ogham.link/`, Individuen `http://data.ogham.link/amt/` | übernommen aus 0.1.0 |
| Gewichtsregel | v1 unverändert (c·a, Schwelle 0,60, vier Dezimalen) | 2026-10-30 |
| Gewichte als Anteile oder als unabhängige Grade? | Anteile (Summe 1) bleiben. Eine Einzel-Lesung trägt immer Gewicht 1, die Beschädigung steht im Typ. Keine Regel v2. Als bewusste Eigenschaft und Grenze in Docs und Papern benennen. Neu aufmachen nur, wenn ein Review es verlangt. | 2026-10-30 |
| Standard-Typ ohne Faktor | kein Typ schreiben, die Engine liest Vagueness | Vorschlag 2026-10-30 |
| Inschriften | Eine Datei mit mehreren gelesenen Inschriften (Blackwaterfoot 1) wird je Inschrift gelesen: `ogham:Inscription` ist Subjekt von `hasReading`, `ogham:hasInscription` verbindet den Stein (einfacher Link, kein Gewicht); Gewichte summieren sich je Inschrift auf 1. Zuordnung der `<rdg>` über die Ordnungszahl in der `<note>` des `<app>` ("For the second inscription"). Bei Dateien mit einer Inschrift bleibt der Stein das Subjekt (alte Graphen unverändert). | 2026-11-01 (Flo) |
| Stein ohne CIIC | IRIs und Beschriftung nach Dateiname (`stone_S_MOR_001`); leeres `<idno type="CIIC"/>` zählt nicht als Nummer | Vorschlag 2026-11-01 |
| `<rdg>` ohne `@source` | kein `prov:wasAttributedTo`, kein gemeinsamer Agent; Anzeige "no editor named". Der Name steht nur in der Prosa der `<note>` und wird nicht geparst. | Vorschlag 2026-11-01 |
| Rolle `hasReading` | ohne formale `rdfs:domain` (Subjekt ist Stein oder Inschrift); Hinweis in Definition und Scope Note | Vorschlag 2026-11-01 |
| `@cert` an der Edition | wird von Regel v1 nicht gelesen (Gigha 1, Dyke: `cert="low"`); in Docs als Grenze genannt | 2026-11-01 |
| Docs | Jekyll in `docs/`, Farben #004c55 / #0090a2 und Logo aus `LinkedOpenOgham/logo` | 2026-10-30 |
| Release-Nummer | 0.3.0 (0.2.0 und 0.2.1 am 2026-10-30; 0.1.0 für den Stand davor rückwirkend benannt) | Vorschlag 2026-10-30 |
| Engine-Check | eigener Schritt `check`, nie im Standardlauf | 2026-10-30 |

## A5 Was in welchem Chat hochgeladen wird

Das Bundle enthält Eingaben und Quellcode, nicht die erzeugten Abbildungen und nicht den Runner-Klon:

```
robocopy . %TEMP%\amt-bundle /E /XD .git build __pycache__ .venv /XF *.png *.svg >nul & powershell -Command "Compress-Archive -Path $env:TEMP\amt-bundle\* -DestinationPath amt-bundle.zip -Force"
```

Nicht hochladen: `.venv/`, `.git/`, `build/`, die Abbildungen in `docs/diagrams/`. Für S2 zusätzlich `build/check-report.txt`.

---

# Teil B: Schrittübersicht

| ID | Schritt | Repo | hängt ab von | Status |
|---|---|---|---|---|
| S0 | Festlegungen (Typregel, Methode, IRIs) | tei--epidoc-amt | | erledigt 2026-10-30 (als Vorschlag) |
| S1 | Skelett, Hextupel, Diagramme, Docs, Tests | tei--epidoc-amt | S0 | erledigt 2026-10-30 |
| S2 | Engine-/Runner-Check durch Florian | tei--epidoc-amt | S1 | offen |
| S3 | Axiome: ist Reasoning gewollt? | tei--epidoc-amt | S2 | offen |
| S4 | Einzel-Lesungen: Gewicht und c | tei--epidoc-amt | S1 | erledigt 2026-10-30 (Beschluss: v1 bleibt) |
| S5 | c(r) historischer Lesungen pro Zeichen | tei--epidoc-amt | S1 | offen |
| S6 | Methode in die FW-Ontologie | FW_Ontology | S1 | offen |
| S7 | Release, Zenodo, Pages | tei--epidoc-amt | S2 | offen |
| S8 | Drei Steine aufnehmen (Dyke, Blackwaterfoot 1, Bishop Loch), je Inschrift lesen | tei--epidoc-amt | | erledigt 2026-11-01 |

S8 ist aus der Übergabe S10 des Crosswalk-PRIMER entstanden. S4, S5 und S6 sind voneinander unabhängig und können in beliebiger Reihenfolge laufen, auch vor S2. S3 und S7 warten auf das Ergebnis von S2.

---

# Teil C: Die Schritte

## S1 — Skelett, Hextupel, Diagramme, Docs, Tests

**Ziel:** Ein Repo, das mit `python main.py` Graphen, Abbildungen und Docs erzeugt, mit Hextupel-Annotation nach Engine 0.6.0.

**Abnahme:** zwei Läufe, byte-identisch; Tests grün; Quadrupel gleich 0.1.0; SHACL-Shapes der Engine konform.

### Erledigt 2026-10-30

- Zwei Läufe (PYTHONHASHSEED 1 und 77): Graphen, Docs und Abbildungen byte-identisch (25 Dateien).
- 5 Tests grün (Gewichtssumme, Hextupel vollständig, Typregel, keine Blank Nodes, Determinismus).
- Quadrupel der vier Graphen identisch zu den eingecheckten 0.1.0-Ausgaben; keine nicht-Aussagen-Tripel verloren.
- pyshacl mit den Shapes der Engine (rdfs-Inferenz, advanced): alle vier Graphen konform. Summe der Gewichte je Stein 1,0000.
- Typen: Gigha 1: vier Mal Uncertainty, einmal FuzzinessWobbliness (OG(H)AM-Edition). Coomleagh East: Uncertainty und FuzzinessWobbliness. Garranes: Vagueness (c = 0,92). Ballinrannig 6: kein Typ.
- **Nicht ausgeführt:** der Runner/die Engine selbst (siehe A1, letzter Befund).

## S2 — Engine-/Runner-Check

**Ziel:** Bestätigung, dass Runner und Engine 0.6.0 die vier Graphen laden und keine Diagnose (`AMT-E101`, `AMT-E102`, `AMT-E103`, `AMT-N301`) melden.

**Uploads:** `build/check-report.txt`.

```
python main.py --only check
```

Der Schritt klont den Runner nach `build/`, ruft je Graph `run_amt.py <graph> --check-only --update` auf und schreibt `build/check-report.txt`. Er braucht Git und Netz.

**Abnahme:** Exit-Code 0 für alle vier Graphen. Bei Befunden: Meldung in den Chat, Fix in `step_convert.py`.

## S3 — Axiome

**Ziel:** Entscheidung, ob die Graphen Axiome bekommen, damit die Engine etwas schließen kann.

Vorschläge, noch nicht beschlossen:

- Rolle teilen in `hasEditionReading` und `hasHistoricalReading`, beide Subsumtion unter `hasReading`. Dann kann die Engine mit `--minimal` die Unterrolle bevorzugen.
- Rollenkette Stein, `hasReading`, Lesung, `wasAttributedTo`, Bearbeiter: abgeleitete Rolle `readByEditor`. Gewicht über das Produkt der Kette, dazu muss geklärt sein, ob die Attribution ein Gewicht trägt (Vorschlag: 1,0).

**Abnahme:** Entscheidung in A4; falls ja: Engine-Lauf mit mindestens einer abgeleiteten Kante pro Stein, Gewichte nachgerechnet.

## S4 — Einzel-Lesungen

**Ziel:** Entscheidung über Garranes-artige Fälle.

**Abnahme:** Beschluss in A4; Docs und README erklären die Eigenschaft.

### Erledigt 2026-10-30

Beschluss: Regel v1 bleibt, Gewichte sind Anteile. Umgesetzt in 0.2.1: Abschnitt „What the weight does not say" auf der Seite Weights, Review-Frage 4 umformuliert, Hinweis in der README, Eintrag im CHANGELOG. Kein Code der Gewichte angefasst, alle Graphen byte-identisch zu 0.2.0. Falls ein Review unabhängige Grade verlangt: neue Regel v2 mit eigenem Methoden-Individuum, v1 bleibt reproduzierbar.

## S5 — c(r) pro Zeichen

**Ziel:** Das Proxy für historische Lesungen (Anteil sauberer Zeichen) durch Zeichen-Sicherheiten ersetzen, wie bei der OG(H)AM-Edition.

**Abnahme:** Gewichte neu, Änderungen im CHANGELOG, Quadrupel-Vergleich gegen die Vorversion mit begründeter Differenzliste.

## S6 — Methode in die FW-Ontologie

**Ziel:** `ConfidenceAgreementRule` als Individuum in `FW_Ontology`, damit kein Repo-eigener Namensraum nötig ist.

**Abnahme:** Individuum in der FW-Ontologie, `fw:hasMethod` im Graphen zeigt auf die w3id-IRI.

## S7 — Release

**Ziel:** Release 0.2.0 (oder höher), Zenodo-DOI in `CITATION.cff` und README, GitHub Pages auf `/docs` aktiviert.

**Abnahme:** Docs unter der Pages-URL erreichbar, DOI aufgelöst, `CITATION.cff` validiert.

---

## S8 — Drei Steine aufnehmen

**Ziel:** Dyke, Blackwaterfoot 1 und Bishop Loch wie die vier alten Steine behandelt (Graph, Docs, Abbildung, Tests), mit denselben Basisnamen wie im Crosswalk.

**Abnahme:** `python main.py` läuft, Tests grün; drei neue `out/*.amt.ttl`; Gewichte je Stein bzw. Inschrift 1; die vier alten Graphen unterscheiden sich nur um die Ontologie-Tripel; zweiter Lauf ändert nichts.

### Erledigt 2026-11-01

- Befund: Blackwaterfoot 1 hat zwei gelesene Inschriften in einer Datei; die `<rdg>` gehören laut `<note>` zur ersten bzw. zweiten. Ohne Trennung wären sie Alternativen voneinander gewesen. Beschluss (Flo): je Inschrift ein Subjekt (A4).
- Ergebnis: Dyke 1 Lesung (c 0,68, Gewicht 1,0000, Vagueness); Bishop Loch 1 Lesung (c 0,60, Gewicht 1,0000, Vagueness); Blackwaterfoot 1 Inschrift 1 vier Lesungen (0,3077 / 0,2769 / 0,2769 / 0,1385), Inschrift 2 vier Lesungen (0,3913 / 0,2609 / 0,2174 / 0,1304).
- Die vier alten Graphen: keine Aussage verändert; entfernt und hinzugefügt sind nur Ontologie-Tripel (neues Konzept, Link, umformulierte Definitionen). Abbildungen 01 bis 04 inhaltlich gleich (nur Clip-IDs), 05 neu.
- Neun Tests grün (vier neu). Zwei Läufe identisch.
- **Bishop Loch ist die Grenze der Methode:** Gewicht 1,0000 und Typ Vagueness sagen nichts über die Zweifel am Objekt, die nur in der Prosa stehen. Steht auf der Seite Stones und Weights.
- **Nicht ausgeführt:** Engine-/Runner-Check (S2), jetzt für sieben Graphen.

# Teil D: Offene Punkte

- **D1 erledigt** (2026-10-30, siehe A4 und S4). Für die Paper: die Grenze des Anteil-Modells offen ansprechen.
- **D2 Zuordnung der Faktoren zu den Typen.** Ist "markierte Zeichen" wirklich Vagueness und "Dissens der Editoren" wirklich Uncertainty? Das ist eine inhaltliche Entscheidung, die gegengeprüft werden sollte (FW-Ontologie, Samian-Beispiel).
- **D3 Datenlizenz** der EpiDoc-Eingaben (OG(H)AM-Projekt) und Lizenz des Logos fehlen. Die Docs binden das Logo ein.
- **D4 erledigt** (2026-11-01): ORCID und Affiliation in `CITATION.cff`.
- **D5 Papiere.** ArcheoFOSS (Jahr bitte bestätigen, im Chat stand 2025) und UK CAA: Welche Abbildungen kommen hinein (Vorschlag: `02_hextuple`, `04_gigha`, `05_spectrum`), und wird die Grenze des Anteil-Modells (D1) dort diskutiert? Vorschlag: ja, in einem Satz.
- **D7 `ogham:recordStatus` im AMT-Graphen?** Der Crosswalk exportiert X/L-Status und Zweifelsprofil am Stein; hier fehlt beides. Für das Poster könnte eine Abfrage über beide Repos reichen. Falls nicht: Status aus dem Bezeichner in `ogham-amt.ttl` aufnehmen (gleicher Begriff, gleicher Vorschlag-Status).
- **D8 Quelle der `<rdg>` ohne `@source`.** Vier Lesungen bei Blackwaterfoot 1 nennen den Bearbeiter nur in der Prosa (Jackson 1973, Forsyth 1996). Entweder die Daten ergänzen (`@source` im OG(H)AM-Repo, Rückmeldung an das OG(H)AM-Team, `lguariento/og-h-am`) oder bewusst ohne Agent lassen.
- **D9 `@cert` an der Edition.** Gigha 1 und Dyke tragen `cert="low"`; Regel v1 liest es nicht. Soll `cert` in c(r) eingehen (Regel v2, eigenes Methoden-Individuum)? Verwandt mit D2 und mit der Grenze bei Bishop Loch.
- **D10 `hasReading` ohne Domain.** Der Engine-Check (S2) zeigt, ob Runner/Engine das akzeptieren. Falls nicht: Union-Klasse oder zweite Rolle für Inschriften.
- **D11 Abbildungen und Matplotlib.** Die eingecheckten Bilder stammen aus Matplotlib 3.9.2 (`requirements.txt` nennt 3.11, das ist falsch); Clip-IDs ändern sich je Plattform. Nur Bilder committen, deren Inhalt sich geändert hat (`05_spectrum`).
- **D6 Rückwirkende Release-Nummer.** Gab es für den Stand vor dieser Arbeit einen Tag 0.1.0? Falls nein, CHANGELOG-Eintrag anpassen.
