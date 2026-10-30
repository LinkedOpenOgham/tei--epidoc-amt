"""Tiny drawing kit for Mermaid-like diagrams, built on matplotlib.

Boxes, ovals and labelled arrows in data coordinates (equal aspect), in the
colour scheme of the Linked Open Ogham logo (LinkedOpenOgham/logo): dark teal
#004c55 and bright teal #0090a2, with white. Light tints of the bright teal fill
the individuals.

Copied from CHNT2026-amt (py/diagram_kit.py) and recoloured; the drawing
functions are the same. Output is deterministic: SVG text is converted to paths,
the hash salt is fixed and no date is embedded.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch  # noqa: E402

plt.rcParams.update({
    "svg.fonttype": "path",
    "svg.hashsalt": "ogham-amt",
    "font.family": "DejaVu Sans",
})

DARK = "#004c55"      # logo, dark
BRIGHT = "#0090a2"    # logo, bright
TINT = "#d9eef1"      # 15 % of the bright teal on white: individuals
MID = "#66bcc7"       # 60 % of the bright teal on white: second step of the type scale
MUTED = "#3f6168"     # secondary text
WHITE = "#ffffff"

# (fill, stroke, text) per node kind
STYLE = {
    "class":    (DARK, DARK, WHITE),      # Concepts     (dark teal)
    "role":     (BRIGHT, DARK, WHITE),    # Roles        (bright teal)
    "instance": (TINT, DARK, DARK),       # Individuals  (light tint, oval)
    "term":     (WHITE, BRIGHT, DARK),    # FW terms     (white, bright outline)
    "axiom":    (WHITE, DARK, DARK),      # plain boxes  (white, dark outline)
}


def new_canvas(width_in: float, height_in: float, xlim: tuple, ylim: tuple):
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    return fig, ax


def node(ax, cx, cy, w, h, text, kind, *, shape="round", size=10, bold=True,
         sub=None, sub_size=8, dashed=False, edge=None, lw=1.6):
    """Draw a node and return its geometry (for arrows)."""
    fill, stroke, fg = STYLE[kind]
    stroke = edge or stroke
    ls = (0, (4, 2)) if dashed else "-"
    if shape == "oval":
        ax.add_patch(Ellipse((cx, cy), w, h, fc=fill, ec=stroke, lw=lw, ls=ls, zorder=3))
    else:
        r = 0.45 if shape == "round" else min(h / 2, 0.6)
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                    boxstyle=f"round,pad=0,rounding_size={r}",
                                    fc=fill, ec=stroke, lw=lw, ls=ls, zorder=3))
    dy = 0.17 if sub else 0
    ax.text(cx, cy + dy, text, ha="center", va="center", color=fg, fontsize=size,
            fontweight="bold" if bold else "normal", zorder=4)
    if sub:
        ax.text(cx, cy - 0.27, sub, ha="center", va="center", color=fg,
                fontsize=sub_size, zorder=4)
    return {"cx": cx, "cy": cy, "w": w, "h": h,
            "top": (cx, cy + h / 2), "bottom": (cx, cy - h / 2),
            "left": (cx - w / 2, cy), "right": (cx + w / 2, cy)}


def arrow(ax, p0, p1, label=None, *, color=DARK, dashed=False, rad=0.0, lw=1.8,
          t=0.5, label_dy=0.0, label_dx=0.0, size=9, label_color=None, head=14,
          boxed=True):
    """Arrow from p0 to p1 (arc3 curvature rad), optional label at curve parameter t."""
    ax.add_patch(FancyArrowPatch(p0, p1, connectionstyle=f"arc3,rad={rad}",
                                 arrowstyle="-|>", mutation_scale=head, color=color, lw=lw,
                                 ls=(0, (5, 3)) if dashed else "-", zorder=2,
                                 shrinkA=0, shrinkB=0))
    if label:
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2 + rad * dy, (y0 + y1) / 2 - rad * dx   # arc3 control point
        px = (1 - t) ** 2 * x0 + 2 * t * (1 - t) * cx + t ** 2 * x1
        py = (1 - t) ** 2 * y0 + 2 * t * (1 - t) * cy + t ** 2 * y1
        ax.text(px + label_dx, py + label_dy, label, ha="center", va="center", fontsize=size,
                color=label_color or DARK, zorder=5,
                bbox=dict(fc="white", ec="none", pad=1.5) if boxed else None)


def legend(ax, x, y, items, *, size=9, gap=3.6):
    """items: list of (kind, text); kind is 'solid', 'dashed', 'bright' or a STYLE key."""
    for i, (kind, text) in enumerate(items):
        xx = x + i * gap
        if kind in ("solid", "dashed", "bright"):
            arrow(ax, (xx, y), (xx + 0.9, y), color=BRIGHT if kind == "bright" else DARK,
                  dashed=kind == "dashed", head=11)
        else:
            fill, stroke, _ = STYLE[kind]
            ax.add_patch(FancyBboxPatch((xx, y - 0.2), 0.9, 0.4,
                                        boxstyle="round,pad=0,rounding_size=0.12",
                                        fc=fill, ec=stroke, lw=1.2, zorder=3))
        ax.text(xx + 1.1, y, text, va="center", ha="left", fontsize=size, color=DARK)


def save(fig, stem):
    from ogham_amt_utils import IMG
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / f"{stem}.svg", format="svg", metadata={"Date": None})
    fig.savefig(IMG / f"{stem}.png", dpi=170, metadata={"Software": None})
    plt.close(fig)
