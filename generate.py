#!/usr/bin/env python3
"""Generate a full deck of playing cards as standalone SVG files.

Usage:  python3 generate.py [output_dir]

Writes 52 cards (e.g. AS.svg, 10H.svg), two jokers, a card back, and a
preview.html sheet showing the whole deck. No dependencies beyond Python.
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- Geometry --------------------------------------------------------------
W, H = 250, 350          # poker size ratio 2.5 : 3.5
RADIUS = 16
MARGIN = 12              # inner border inset
PIP = 46                 # size of a normal pip
CORNER_PIP = 22
BIG_PIP = 130            # ace centre pip

# --- Colours ---------------------------------------------------------------
RED = "#c8102e"
BLACK = "#1c1c1c"
PAPER = "#fdfcf8"
GOLD = "#b8912e"
BACK_A = "#1f3a5f"
BACK_B = "#e8dcc4"

SUITS = {
    "S": ("spades", BLACK),
    "H": ("hearts", RED),
    "D": ("diamonds", RED),
    "C": ("clubs", BLACK),
}
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

# Suit glyphs drawn inside a 100x100 box, centred on (50, 50).
SUIT_PATHS = {
    "hearts": (
        "M50,92 C22,68 6,52 6,32 C6,17 18,6 32,6 C41,6 47,11 50,19 "
        "C53,11 59,6 68,6 C82,6 94,17 94,32 C94,52 78,68 50,92 Z"
    ),
    "diamonds": "M50,4 L92,50 L50,96 L8,50 Z",
    "spades": (
        "M50,6 C78,32 94,46 94,63 C94,77 84,87 71,87 C63,87 56,83 52,77 "
        "C53,86 58,92 66,96 L34,96 C42,92 47,86 48,77 C44,83 37,87 29,87 "
        "C16,87 6,77 6,63 C6,46 22,32 50,6 Z"
    ),
    "clubs": (
        "M50,7 A19,19 0 1 1 49.9,7 Z "
        "M28,50 A19,19 0 1 1 27.9,50 Z "
        "M72,50 A19,19 0 1 1 71.9,50 Z "
        "M50,52 C52,74 57,88 66,96 L34,96 C43,88 48,74 50,52 Z"
    ),
}

# Pip layout grid. Columns: L C R.  Rows are fractions of the pip area height.
L, C, R = 0.0, 0.5, 1.0
ROWS = {
    "top": 0.0, "upper": 0.25, "mid": 0.5, "lower": 0.75, "bottom": 1.0,
    "q1": 1 / 6, "q3": 5 / 6,   # for 9 and 10 (four rows of side pips)
    "u2": 1 / 3, "l2": 2 / 3,
}

PIP_LAYOUTS: dict[str, list[tuple[float, str]]] = {
    "2": [(C, "top"), (C, "bottom")],
    "3": [(C, "top"), (C, "mid"), (C, "bottom")],
    "4": [(L, "top"), (R, "top"), (L, "bottom"), (R, "bottom")],
    "5": [(L, "top"), (R, "top"), (C, "mid"), (L, "bottom"), (R, "bottom")],
    "6": [(L, "top"), (R, "top"), (L, "mid"), (R, "mid"), (L, "bottom"), (R, "bottom")],
    "7": [(L, "top"), (R, "top"), (C, "upper"), (L, "mid"), (R, "mid"),
          (L, "bottom"), (R, "bottom")],
    "8": [(L, "top"), (R, "top"), (C, "upper"), (L, "mid"), (R, "mid"),
          (C, "lower"), (L, "bottom"), (R, "bottom")],
    "9": [(L, "top"), (R, "top"), (L, "u2"), (R, "u2"), (C, "mid"),
          (L, "l2"), (R, "l2"), (L, "bottom"), (R, "bottom")],
    "10": [(L, "top"), (R, "top"), (C, "q1"), (L, "u2"), (R, "u2"),
           (L, "l2"), (R, "l2"), (C, "q3"), (L, "bottom"), (R, "bottom")],
}


# --- SVG helpers -----------------------------------------------------------
def suit_glyph(suit: str, x: float, y: float, size: float, color: str,
               flip: bool = False) -> str:
    """Suit symbol centred at (x, y) with the given size."""
    s = size / 100
    rot = " rotate(180)" if flip else ""
    return (
        f'<path d="{SUIT_PATHS[suit]}" fill="{color}" '
        f'transform="translate({x:.1f},{y:.1f}){rot} scale({s:.4f}) '
        f'translate(-50,-50)"/>'
    )


def corner_index(rank: str, suit: str, color: str, flip: bool = False) -> str:
    """Rank + suit index in the top-left; rotate 180° for bottom-right."""
    font_size = 34 if rank != "10" else 30
    x = 26
    label = (
        f'<text x="{x}" y="42" font-size="{font_size}" font-weight="700" '
        f'text-anchor="middle" fill="{color}" '
        f'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">{rank}</text>'
    )
    pip = suit_glyph(suit, x, 62, CORNER_PIP, color)
    g = label + pip
    if flip:
        return f'<g transform="rotate(180 {W / 2} {H / 2})">{g}</g>'
    return g


def frame(extra_class: str = "") -> str:
    return (
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="{RADIUS}" '
        f'fill="{PAPER}" stroke="#d9d4c7" stroke-width="1"/>'
    )


def wrap(body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">\n'
        f'  <title>{title}</title>\n'
        f'  {body}\n</svg>\n'
    )


# --- Card faces ------------------------------------------------------------
def pip_area() -> tuple[float, float, float, float]:
    """Return (x0, y0, x1, y1) box that pip centres are placed within."""
    x0, x1 = 72, W - 72
    y0, y1 = 70, H - 70
    return x0, y0, x1, y1


def number_card(rank: str, suit: str, color: str) -> str:
    x0, y0, x1, y1 = pip_area()
    parts = []
    for col, row in PIP_LAYOUTS[rank]:
        fx = ROWS[row]
        x = x0 + col * (x1 - x0)
        y = y0 + fx * (y1 - y0)
        parts.append(suit_glyph(suit, x, y, PIP, color, flip=fx > 0.5))
    return "".join(parts)


def ace_card(suit: str, color: str) -> str:
    size = BIG_PIP if suit != "spades" else BIG_PIP + 20
    body = suit_glyph(suit, W / 2, H / 2, size, color)
    if suit == "spades":
        # Traditional ornamental ace of spades: a ring around the pip.
        body = (
            f'<circle cx="{W / 2}" cy="{H / 2}" r="98" fill="none" '
            f'stroke="{color}" stroke-width="1.5"/>'
            f'<circle cx="{W / 2}" cy="{H / 2}" r="92" fill="none" '
            f'stroke="{color}" stroke-width="0.75"/>'
            + body
        )
    return body


def crown(color: str, kind: str) -> str:
    """Simple crown shapes drawn in a 100x60 box, origin top-left."""
    if kind == "K":
        path = ("M8,56 L8,22 L28,38 L50,6 L72,38 L92,22 L92,56 Z "
                "M8,56 L92,56 L92,48 L8,48 Z")
        gems = ('<circle cx="50" cy="6" r="4"/><circle cx="8" cy="22" r="4"/>'
                '<circle cx="92" cy="22" r="4"/>')
    elif kind == "Q":
        path = ("M10,56 L10,26 C22,26 30,34 34,44 C36,20 44,10 50,8 "
                "C56,10 64,20 66,44 C70,34 78,26 90,26 L90,56 Z "
                "M10,56 L90,56 L90,48 L10,48 Z")
        gems = ('<circle cx="50" cy="8" r="4.5"/><circle cx="10" cy="26" r="4"/>'
                '<circle cx="90" cy="26" r="4"/>')
    else:  # Jack: a cap with a feather
        path = ("M14,52 C14,30 30,16 50,16 C70,16 86,30 86,52 Z "
                "M8,52 L92,52 L92,58 L8,58 Z "
                "M62,20 C70,4 84,0 96,4 C88,10 82,18 76,26 Z")
        gems = '<circle cx="50" cy="16" r="3.5"/>'
    return f'<g fill="{color}">{path and f"<path d=\"{path}\"/>"}{gems}</g>'


def face_card(rank: str, suit: str, color: str) -> str:
    """Court cards: a framed panel with crown and monogram, mirrored top/bottom."""
    px0, py0 = 46, 62
    pw, ph = W - 2 * px0, H - 2 * py0
    cx, cy = W / 2, H / 2
    tint = "#f3ede0"
    parts = [
        f'<rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" rx="6" '
        f'fill="{tint}" stroke="{GOLD}" stroke-width="2"/>',
        f'<rect x="{px0 + 5}" y="{py0 + 5}" width="{pw - 10}" height="{ph - 10}" '
        f'rx="3" fill="none" stroke="{GOLD}" stroke-width="0.75"/>',
    ]
    # One half is drawn upright in the top half of the panel (y 62..175),
    # then repeated rotated 180 degrees for the bottom half.
    crown_scale = 0.72                       # 100x60 box -> 72x43
    crown_y = py0 + 14
    letter_baseline = py0 + 104              # 166: cap height stays above centre
    half = (
        f'<g transform="translate({cx - 50 * crown_scale},{crown_y}) '
        f'scale({crown_scale})">{crown(color, rank)}</g>'
        f'<text x="{cx}" y="{letter_baseline}" font-size="56" font-weight="700" '
        f'text-anchor="middle" fill="{color}" '
        f'font-family="Georgia, Times New Roman, serif">{rank}</text>'
        + suit_glyph(suit, cx - 52, letter_baseline - 18, 24, color)
        + suit_glyph(suit, cx + 52, letter_baseline - 18, 24, color)
    )
    parts.append(half)
    parts.append(f'<g transform="rotate(180 {cx} {cy})">{half}</g>')
    # thin rule across the middle to separate the two halves
    parts.append(
        f'<line x1="{px0 + 14}" y1="{cy}" x2="{px0 + pw - 14}" y2="{cy}" '
        f'stroke="{GOLD}" stroke-width="0.75"/>'
    )
    return "".join(parts)


def card_svg(rank: str, suit_key: str) -> str:
    suit, color = SUITS[suit_key]
    if rank == "A":
        centre = ace_card(suit, color)
    elif rank in PIP_LAYOUTS:
        centre = number_card(rank, suit, color)
    else:
        centre = face_card(rank, suit, color)
    body = (
        frame()
        + corner_index(rank, suit, color)
        + corner_index(rank, suit, color, flip=True)
        + centre
    )
    names = {"A": "Ace", "J": "Jack", "Q": "Queen", "K": "King"}
    title = f"{names.get(rank, rank)} of {suit.capitalize()}"
    return wrap(body, title)


# --- Jokers and back -------------------------------------------------------
def joker_svg(color: str, label: str) -> str:
    cx, cy = W / 2, H / 2
    # A jester's hat: three curved points with bells.
    hat = (
        f'<g transform="translate({cx - 60},{cy - 90})" fill="{color}">'
        '<path d="M60,120 L10,110 C0,70 20,40 8,10 C40,30 50,60 60,70 '
        'C70,40 90,20 112,10 C100,40 120,70 110,110 Z"/>'
        '<circle cx="8" cy="10" r="9"/><circle cx="112" cy="10" r="9"/>'
                '</g>'
        f'<rect x="{cx - 46}" y="{cy + 26}" width="92" height="12" rx="6" fill="{GOLD}"/>'
    )
    text = "".join(
        f'<text x="26" y="{50 + i * 24}" font-size="20" font-weight="700" '
        f'text-anchor="middle" fill="{color}" '
        f'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">{ch}</text>'
        for i, ch in enumerate("JOKER")
    )
    flipped = f'<g transform="rotate(180 {cx} {cy})">{text}</g>'
    body = frame() + text + flipped + hat
    return wrap(body, f"{label} Joker")


def back_svg() -> str:
    m = 14
    body = (
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="{RADIUS}" '
        f'fill="{PAPER}" stroke="#d9d4c7"/>'
        '<defs>'
        '<pattern id="weave" width="20" height="20" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)">'
        f'<rect width="20" height="20" fill="{BACK_A}"/>'
        f'<rect width="10" height="10" fill="{BACK_B}" opacity="0.18"/>'
        f'<rect x="10" y="10" width="10" height="10" fill="{BACK_B}" opacity="0.18"/>'
        '</pattern>'
        '</defs>'
        f'<rect x="{m}" y="{m}" width="{W - 2 * m}" height="{H - 2 * m}" rx="8" '
        'fill="url(#weave)"/>'
        f'<rect x="{m + 8}" y="{m + 8}" width="{W - 2 * m - 16}" '
        f'height="{H - 2 * m - 16}" rx="5" fill="none" stroke="{BACK_B}" '
        'stroke-width="2"/>'
        f'<ellipse cx="{W / 2}" cy="{H / 2}" rx="62" ry="86" fill="{BACK_A}" '
        f'stroke="{BACK_B}" stroke-width="2"/>'
        + "".join(
            suit_glyph(s, W / 2 + dx, H / 2 + dy, 30, BACK_B)
            for s, dx, dy in (("spades", 0, -48), ("hearts", -30, 0),
                              ("diamonds", 30, 0), ("clubs", 0, 48))
        )
    )
    return wrap(body, "Card back")


# --- Preview sheet ---------------------------------------------------------
def preview_html(files: list[str]) -> str:
    imgs = "\n".join(
        f'<figure><img src="{f}" alt="{f}"><figcaption>{f}</figcaption></figure>'
        for f in files
    )
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Deck preview</title>
<style>
  body {{ margin: 24px; background: #2a2a2e; color: #ddd;
         font: 13px/1.4 system-ui, sans-serif; }}
  h1 {{ font-weight: 500; margin: 0 0 16px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
           gap: 14px; }}
  figure {{ margin: 0; text-align: center; }}
  img {{ width: 100%; height: auto; border-radius: 8px;
         box-shadow: 0 4px 12px rgba(0,0,0,.5); background: #fff; }}
  figcaption {{ margin-top: 4px; opacity: .6; }}
</style>
<h1>Deck preview ({len(files)} cards)</h1>
<div class="grid">
{imgs}
</div>
"""


# --- Main ------------------------------------------------------------------
def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "deck")
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for suit_key in SUITS:
        for rank in RANKS:
            name = f"{rank}{suit_key}.svg"
            (out / name).write_text(card_svg(rank, suit_key))
            written.append(name)

    (out / "joker_red.svg").write_text(joker_svg(RED, "Red"))
    (out / "joker_black.svg").write_text(joker_svg(BLACK, "Black"))
    (out / "back.svg").write_text(back_svg())
    written += ["joker_red.svg", "joker_black.svg", "back.svg"]

    (out / "preview.html").write_text(preview_html(written))
    print(f"Wrote {len(written)} SVGs + preview.html to {out}/")


if __name__ == "__main__":
    main()
