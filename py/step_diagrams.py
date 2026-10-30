#!/usr/bin/env python3
"""Step "diagrams": draw the figures into docs/diagrams/ (SVG + PNG).

  01_model       the two concepts, the role, the PROV link          (simple view)
  02_hextuple    one reading as a hextuple, from the real data       (full semantics)
  03_weighting   from the EpiDoc markup to amt:weight and fw:hasType
  04_gigha       Gigha 1: one stone, five competing readings, with weights and types
  05_spectrum    the four stones side by side, one bar per stone, one segment per reading

Everything that has a name in the ontology or a value in the data is read from
there; only the positions are fixed here. Colours are those of the Linked Open
Ogham logo (py/diagram_kit.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from diagram_kit import BRIGHT, DARK, MID, MUTED, TINT, WHITE, arrow, legend, new_canvas, node, save  # noqa: E402
from ogham_amt_utils import DATA, STONES, TYPE_CURIE, TYPE_TAG, slug  # noqa: E402
from step_convert import analyse, local_names, reading_type  # noqa: E402

W = 12.5                      # figure width in inches; narrower than the page, so the type reads larger
XLIM = (-0.4, 22.6)


def canvas(height_units: float):
    return new_canvas(W, W * height_units / (XLIM[1] - XLIM[0]), XLIM, (0.0, height_units))


def title(ax, y, text):
    ax.text(0.0, y, text, fontsize=14, fontweight="bold", va="center", color=DARK)


def ordered(readings):
    return sorted(readings, key=lambda r: (-r.weight, r.source_id))


# ── 01 ───────────────────────────────────────────────────────────────────────
def figure_model():
    fig, ax = canvas(5.8)
    title(ax, 5.3, "Linked Open Ogham AMT model - simple view")
    y0 = 3.1
    stone = node(ax, 3.4, y0, 4.8, 1.5, "OghamStone", "class", size=11)
    reading = node(ax, 11.3, y0, 4.8, 1.5, "Reading", "class", size=11)
    agent = node(ax, 19.2, y0, 4.8, 1.5, "prov:Agent", "axiom", size=11, sub="the editor")
    xa, xb = stone["right"][0] + 0.1, reading["left"][0] - 0.1
    arrow(ax, (xa, y0), (xb, y0), "hasReading", label_dy=0.42, boxed=False, size=11)
    ax.text((xa + xb) / 2, y0 - 0.55, "amt:weight\nfw:hasType, fw:hasMethod", ha="center", va="center",
            fontsize=8.5, color=MUTED)
    arrow(ax, (reading["right"][0] + 0.1, y0), (agent["left"][0] - 0.1, y0), "prov:\nwasAttributedTo",
          color=BRIGHT, dashed=True, label_dy=0.62, boxed=False, size=10)
    ax.text(11.3, 1.35, "One statement per reading. The weights of the readings of one stone add up to 1.",
            ha="center", fontsize=9, color=MUTED)
    legend(ax, 0.0, 0.5, [("class", "class (amt:Concept)"), ("solid", "weighted statement (hextuple)"),
                          ("bright", "plain RDF link (PROV)"), ("axiom", "external class")], gap=5.6)
    save(fig, "01_model")


# ── 02 ───────────────────────────────────────────────────────────────────────
def figure_hextuple(results):
    stone, readings, _ = next(r for r in results if len(r[1]) > 1)
    names = local_names(stone, readings)
    i = max(range(len(readings)), key=lambda k: readings[k].weight)
    r, n = readings[i], names[i]
    ciic = slug(stone.get("CIIC", "stone"))
    t = reading_type(r)
    fig, ax = canvas(11.6)
    title(ax, 11.0, f"A reading as a hextuple ({stone.get('title', '')}, CIIC {stone.get('CIIC', '')})")
    mid = 5.9
    stmt = node(ax, 11.2, mid, 4.4, 2.2, "Statement", "axiom", size=11, sub=f"data:{n['statement']}", sub_size=7.5)
    subj = node(ax, 3.4, 9.5, 5.4, 1.6, f"stone_{ciic}", "instance", shape="oval", sub="OghamStone")
    pred = node(ax, 3.4, mid, 5.4, 1.5, "hasReading", "role", shape="pill", sub="OghamStone -> Reading")
    obj = node(ax, 3.4, 2.3, 5.8, 1.7, n["reading"].replace("reading_", "reading_"), "instance",
               shape="oval", sub="Reading", size=9.5)
    wt = node(ax, 19.2, 10.1, 5.4, 1.4, f"{r.weight:.4f}", "axiom", sub="xsd:decimal")
    ty = node(ax, 19.2, 8.0, 5.4, 1.4, TYPE_CURIE[t] if t else "no type", "term",
              sub="fw:FW_Type" if t else "AMT reads fw:Vagueness", size=10)
    me = node(ax, 19.2, 5.7, 6.2, 1.6, "ConfidenceAgreementRule", "term", sub="fw:RuleBasedMethod", size=10)
    ev = node(ax, 19.2, 2.9, 6.2, 2.0, "fw:TextEvidence", "term",
              sub=f"\"{r.text}\"" if len(r.text) <= 26 else f"\"{r.text[:24]}...\"", size=10)
    for target, label, t_pos in ((subj, "rdf:subject", 0.5), (pred, "rdf:predicate", 0.5), (obj, "rdf:object", 0.5)):
        arrow(ax, (stmt["left"][0] - 0.1, stmt["left"][1]), (target["right"][0] + 0.1, target["right"][1]),
              label, t=t_pos, size=9)
    for target, label in ((wt, "amt:weight"), (ty, "fw:hasType"), (me, "fw:hasMethod"), (ev, "fw:derivedFrom")):
        arrow(ax, (stmt["right"][0] + 0.1, stmt["right"][1]), (target["left"][0] - 0.1, target["left"][1]),
              label, t=0.52, size=9)
    ax.text(0.0, 0.95, "fw:hasType names the factor that pulled the raw weight below 1: c < 1 vagueness, "
            "a < 1 uncertainty, both fuzziness-wobbliness.", fontsize=8.5, color=MUTED, va="center")
    legend(ax, 0.0, 0.3, [("instance", "individual"), ("role", "role (amt:Role)"),
                          ("term", "FW term, method, evidence"), ("axiom", "statement, literal")], gap=5.6)
    save(fig, "02_hextuple")


# ── 03 ───────────────────────────────────────────────────────────────────────
def figure_weighting():
    fig, ax = canvas(8.6)
    title(ax, 8.0, "From the EpiDoc markup to amt:weight and fw:hasType")
    gap = 0.1
    xml = node(ax, 2.6, 4.3, 4.2, 1.7, "EpiDoc", "class", sub="OG(H)AM TEI/XML")
    mk = node(ax, 9.0, 6.3, 5.6, 1.7, "markup of a reading", "axiom", sub="unclear, supplied, gap, editor marks", size=10)
    al = node(ax, 9.0, 2.3, 5.6, 1.7, "all readings of the stone", "axiom", sub="compared by string similarity, >= 0.60", size=10, sub_size=7.5)
    c = node(ax, 15.3, 6.3, 4.2, 1.7, "c(r)", "role", sub="reading confidence", size=12)
    a = node(ax, 15.3, 2.3, 4.2, 1.7, "a(r)", "role", sub="tradition agreement", size=12)
    wt = node(ax, 20.6, 5.7, 3.8, 2.0, "amt:weight", "class", sub="c*a, normalised, sum = 1", size=10)
    ty = node(ax, 20.6, 2.5, 3.8, 2.0, "fw:hasType", "term", sub="V, U or FW", size=10)
    arrow(ax, (xml["right"][0] + gap, 4.7), (mk["left"][0] - gap, mk["left"][1]), rad=-0.15)
    arrow(ax, (xml["right"][0] + gap, 3.9), (al["left"][0] - gap, al["left"][1]), rad=0.15)
    arrow(ax, (mk["right"][0] + gap, 6.3), (c["left"][0] - gap, 6.3))
    arrow(ax, (al["right"][0] + gap, 2.3), (a["left"][0] - gap, 2.3))
    arrow(ax, (c["right"][0] + gap, 6.3), (wt["left"][0] - gap, 6.1))
    arrow(ax, (a["right"][0] + gap, 2.5), (wt["left"][0] - gap, 5.3), rad=0.0)
    arrow(ax, (c["right"][0] + gap, 5.6), (ty["left"][0] - gap, 3.0), color=BRIGHT, dashed=True)
    arrow(ax, (a["right"][0] + gap, 2.0), (ty["left"][0] - gap, 2.0), color=BRIGHT, dashed=True)
    ax.text(0.0, 0.95, "c < 1 gives fw:Vagueness, a < 1 fw:Uncertainty, both fw:FuzzinessWobbliness. "
            "Neither: no type is written.", fontsize=8.5, color=MUTED, va="center")
    legend(ax, 0.0, 0.3, [("axiom", "source"), ("role", "factor"), ("class", "AMT result"),
                          ("term", "FW term"), ("dashed", "decides the type")], gap=4.4)
    save(fig, "03_weighting")


# ── 04 ───────────────────────────────────────────────────────────────────────
def figure_gigha(results):
    stone, readings, _ = next(r for r in results if len(r[1]) > 1)
    rs = ordered(readings)
    pitch = 2.1
    height = len(rs) * pitch + 3.4
    fig, ax = canvas(height)
    title(ax, height - 0.5, f"{stone.get('title', '')} (CIIC {stone.get('CIIC', '')}): "
          f"{len(rs)} competing readings, one statement each")
    top = height - 1.5
    mid = top - (len(rs) * pitch) / 2 + pitch / 2 - 0.2
    so = node(ax, 3.6, mid, 5.8, 2.0, f"stone_{slug(stone.get('CIIC', ''))}", "instance", shape="oval", sub="OghamStone")
    for k, r in enumerate(rs):
        y = top - k * pitch - 0.9
        text = r.text if len(r.text) <= 28 else r.text[:26] + "..."
        ro = node(ax, 16.9, y, 10.2, 1.5, text, "instance", shape="oval", size=9.5,
                  sub=f"{r.editor}   c {r.confidence:.2f}   a {r.agreement:.2f}", sub_size=8)
        tag = f"{r.weight:.4f} {TYPE_TAG[reading_type(r)]}".strip()
        arrow(ax, (so["right"][0] + 0.1, so["right"][1]), (ro["left"][0] - 0.1, ro["left"][1]),
              tag, t=0.45, size=9.5, rad=0.0)
    ax.text(0.0, 1.05, "hasReading statements: weight, then type (U uncertainty, V vagueness, FW fuzziness-wobbliness). "
            "c reading confidence, a tradition agreement.", fontsize=8.5, color=MUTED, va="center")
    legend(ax, 0.0, 0.4, [("instance", "individual"), ("solid", "hasReading statement")], gap=5.6)
    save(fig, "04_gigha")


# ── 05 ───────────────────────────────────────────────────────────────────────
SEGMENT = {None: (TINT, DARK), TYPE_TAG and "V": (MID, DARK), "U": (BRIGHT, WHITE), "FW": (DARK, WHITE)}


def figure_spectrum(results):
    fig, ax = plt.subplots(figsize=(W, 1.25 * len(results) + 1.7))
    for k, (stone, readings, _) in enumerate(results):
        y = len(results) - 1 - k
        left = 0.0
        for r in ordered(readings):
            tag = TYPE_TAG[reading_type(r)] or None
            fc, tc = SEGMENT[tag]
            ax.barh(y, r.weight, left=left, height=0.52, color=fc, edgecolor=WHITE, linewidth=2)
            if r.weight >= 0.085:
                ax.text(left + r.weight / 2, y, f"{r.editor}\n{r.weight:.4f}", ha="center", va="center",
                        fontsize=8, fontweight="bold", color=tc)
            left += r.weight
        ax.text(0.0, y + 0.42, f"{stone.get('title', '')} (CIIC {stone.get('CIIC', '')}) - "
                f"{len(readings)} reading{'s' if len(readings) != 1 else ''}",
                fontsize=10.5, fontweight="bold", color=DARK, va="bottom")
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, len(results) - 0.1)
    ax.set_yticks([])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(axis="x", colors=DARK, labelsize=9)
    ax.set_xlabel("share of the weight of the stone (the weights of one stone add up to 1)", color=DARK, fontsize=9)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(DARK)
    ax.set_title("Spectrum of doubt: the readings of four stones, coloured by FW type", loc="left",
                 fontsize=14, fontweight="bold", color=DARK)
    ax.legend(handles=[Patch(fc=TINT, ec=DARK, label="no type (single, unmarked reading)"),
                       Patch(fc=MID, ec=DARK, label="fw:Vagueness (c < 1)"),
                       Patch(fc=BRIGHT, ec=DARK, label="fw:Uncertainty (a < 1)"),
                       Patch(fc=DARK, ec=DARK, label="fw:FuzzinessWobbliness (both)")],
              loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, frameon=False, fontsize=9,
              labelcolor=DARK)
    fig.subplots_adjust(left=0.015, right=0.975, top=0.9, bottom=0.2)
    save(fig, "05_spectrum")


def main() -> int:
    results = [(*analyse(DATA / f), b) for f, b in STONES]
    figure_model()
    figure_hextuple(results)
    figure_weighting()
    figure_gigha(results)
    figure_spectrum(results)
    print("wrote docs/diagrams/01_model, 02_hextuple, 03_weighting, 04_gigha, 05_spectrum (.svg + .png)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
