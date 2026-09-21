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
PIP = 43                 # size of a normal pip
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
        "M50,94 C22,70 6,53 6,32 C6,16 18,5 32,5 C41,5 48,11 50,21 "
        "C52,11 59,5 68,5 C82,5 94,16 94,32 C94,53 78,70 50,94 Z"
    ),
    "diamonds": "M50,3 L86,50 L50,97 L14,50 Z",
    "spades": (
        "M50,6 C78,32 94,46 94,63 C94,77 84,87 71,87 C63,87 56,83 52,77 "
        "C53,86 58,92 66,96 L34,96 C42,92 47,86 48,77 C44,83 37,87 29,87 "
        "C16,87 6,77 6,63 C6,46 22,32 50,6 Z"
    ),
    "clubs": (
        "M50,7 A20,20 0 1 1 49.9,7 Z "
        "M29,39 A20,20 0 1 1 28.9,39 Z "
        "M71,39 A20,20 0 1 1 70.9,39 Z "
        "M50,27 L71,59 L29,59 Z "
        "M50,42 C54,70 58,88 68,97 L32,97 C42,88 46,70 50,42 Z"
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
    """Court emblems drawn in a 100x60 box, origin top-left."""
    if kind == "K":
        # Five-point crown with a jewelled band.
        body = ("M10,44 L10,20 L27,34 L38,10 L50,28 L62,10 L73,34 L90,20 L90,44 Z")
        band = '<rect x="8" y="44" width="84" height="12" rx="3"/>'
        gems = ('<circle cx="10" cy="20" r="4"/><circle cx="38" cy="10" r="4"/>'
                '<circle cx="62" cy="10" r="4"/><circle cx="90" cy="20" r="4"/>')
        jewel = f'<path d="M50,45 L55,50 L50,55 L45,50 Z" fill="{PAPER}"/>'
        return f'<g fill="{color}"><path d="{body}"/>{band}{gems}</g>{jewel}'
    if kind == "Q":
        # Scalloped tiara with pearls.
        body = ("M12,44 L12,24 C22,26 30,32 34,40 C36,22 44,10 50,6 "
                "C56,10 64,22 66,40 C70,32 78,26 88,24 L88,44 Z")
        band = '<rect x="10" y="44" width="80" height="11" rx="3"/>'
        pearls = ('<circle cx="12" cy="23" r="4"/><circle cx="50" cy="6" r="4.5"/>'
                  '<circle cx="88" cy="23" r="4"/>')
        dots = "".join(f'<circle cx="{x}" cy="49.5" r="2.2" fill="{PAPER}"/>'
                       for x in (26, 38, 50, 62, 74))
        return f'<g fill="{color}"><path d="{body}"/>{band}{pearls}</g>{dots}'
    # Jack: a soft cap with a band and a feather.
    dome = "M8,44 C6,28 22,16 46,18 C66,19 84,28 92,44 Z"
    band = '<rect x="6" y="44" width="88" height="11" rx="4"/>'
    feather = "M62,24 C68,8 82,0 100,2 C96,12 86,22 70,30 Z"
    quill = ('<path d="M66,27 C76,16 86,8 98,3" fill="none" '
             f'stroke="{PAPER}" stroke-width="1.6"/>')
    return f'<g fill="{color}"><path d="{dome}"/>{band}<path d="{feather}"/></g>{quill}'


def face_card(rank: str, suit: str, color: str) -> str:
    """Court cards: a framed panel with emblem and monogram, mirrored top/bottom."""
    px0, py0 = 46, 62
    pw, ph = W - 2 * px0, H - 2 * py0
    cx, cy = W / 2, H / 2
    tint = "#f4eee1"
    parts = [
        f'<rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" rx="6" '
        f'fill="{tint}" stroke="{GOLD}" stroke-width="2"/>',
        f'<rect x="{px0 + 5}" y="{py0 + 5}" width="{pw - 10}" height="{ph - 10}" '
        f'rx="3" fill="none" stroke="{GOLD}" stroke-width="0.75"/>',
    ]
    crown_scale = 0.7                        # 100x60 box -> 70x42
    crown_y = py0 + 13
    baseline = py0 + 96                      # 158: descenders stay above centre
    half = (
        f'<g transform="translate({cx - 50 * crown_scale},{crown_y}) '
        f'scale({crown_scale})">{crown(color, rank)}</g>'
        f'<text x="{cx}" y="{baseline}" font-size="50" font-weight="700" '
        f'text-anchor="middle" fill="{color}" '
        f'font-family="Georgia, Times New Roman, serif">{rank}</text>'
        + suit_glyph(suit, cx - 50, baseline - 17, 22, color)
        + suit_glyph(suit, cx + 50, baseline - 17, 22, color)
    )
    parts.append(half)
    parts.append(f'<g transform="rotate(180 {cx} {cy})">{half}</g>')
    # Centre rule with a small gold lozenge.
    parts.append(
        f'<line x1="{px0 + 16}" y1="{cy}" x2="{cx - 9}" y2="{cy}" '
        f'stroke="{GOLD}" stroke-width="0.75"/>'
        f'<line x1="{cx + 9}" y1="{cy}" x2="{px0 + pw - 16}" y2="{cy}" '
        f'stroke="{GOLD}" stroke-width="0.75"/>'
        f'<path d="M{cx},{cy - 4} L{cx + 4},{cy} L{cx},{cy + 4} L{cx - 4},{cy} Z" '
        f'fill="{GOLD}"/>'
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
def joker_svg(color: str, accent: str, label: str) -> str:
    """The joker: a winking face between two arches of juggled suits."""
    cx, cy = W / 2, H / 2
    px0, py0 = 46, 62
    pw, ph = W - 2 * px0, H - 2 * py0
    tint = "#f4eee1"
    panel = (
        f'<rect x="{px0}" y="{py0}" width="{pw}" height="{ph}" rx="6" '
        f'fill="{tint}" stroke="{GOLD}" stroke-width="2"/>'
        f'<rect x="{px0 + 5}" y="{py0 + 5}" width="{pw - 10}" height="{ph - 10}" '
        f'rx="3" fill="none" stroke="{GOLD}" stroke-width="0.75"/>'
    )
    r = 34
    face = (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PAPER}" stroke="{color}" stroke-width="3"/>'
        f'<circle cx="{cx - 22}" cy="{cy + 10}" r="4" fill="{accent}"/>'
        f'<circle cx="{cx + 22}" cy="{cy + 10}" r="4" fill="{accent}"/>'
        f'<path d="M{cx - 22},{cy - 13} Q{cx - 14},{cy - 20} {cx - 6},{cy - 14}" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
        f'<path d="M{cx + 5},{cy - 17} Q{cx + 14},{cy - 25} {cx + 23},{cy - 17}" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
        f'<circle cx="{cx - 14}" cy="{cy - 3}" r="3.6" fill="{color}"/>'
        f'<path d="M{cx + 6},{cy - 2} Q{cx + 14},{cy - 8} {cx + 22},{cy - 2}" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
        f'<path d="M{cx},{cy} L{cx - 4},{cy + 8} L{cx + 4},{cy + 8}" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<path d="M{cx - 18},{cy + 13} Q{cx},{cy + 33} {cx + 18},{cy + 13}" fill="none" '
        f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
        f'<path d="M{cx - 13},{cy + 15} Q{cx},{cy + 23} {cx + 13},{cy + 15}" fill="{PAPER}"/>'
    )
    # An arch of the four suits above the face; the same arch rotated below.
    P0, P1, P2 = (60, 156), (125, 40), (190, 156)

    def bez(t):
        x = (1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * P1[0] + t * t * P2[0]
        y = (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * P1[1] + t * t * P2[1]
        return x, y

    arch = (
        f'<path d="M{P0[0]},{P0[1]} Q{P1[0]},{P1[1]} {P2[0]},{P2[1]}" '
        f'fill="none" stroke="{GOLD}" stroke-width="1.2" stroke-dasharray="3 4"/>'
        + "".join(
            suit_glyph(suit, *bez(t), 22, col)
            for suit, col, t in (("spades", BLACK, 0.06), ("hearts", RED, 0.34),
                                 ("diamonds", RED, 0.66), ("clubs", BLACK, 0.94))
        )
    )
    arches = arch + f'<g transform="rotate(180 {cx} {cy})">{arch}</g>'
    text = "".join(
        f'<text x="26" y="{50 + i * 24}" font-size="20" font-weight="700" '
        f'text-anchor="middle" fill="{color}" '
        f'font-family="Helvetica Neue, Helvetica, Arial, sans-serif">{ch}</text>'
        for i, ch in enumerate("JOKER")
    )
    flipped = f'<g transform="rotate(180 {cx} {cy})">{text}</g>'
    body = frame() + panel + text + flipped + arches + face
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

    (out / "joker_red.svg").write_text(joker_svg(RED, GOLD, "Red"))
    (out / "joker_black.svg").write_text(joker_svg(BLACK, "#9a9a9a", "Black"))
    (out / "back.svg").write_text(back_svg())
    written += ["joker_red.svg", "joker_black.svg", "back.svg"]

    (out / "preview.html").write_text(preview_html(written))
    print(f"Wrote {len(written)} SVGs + preview.html to {out}/")


if __name__ == "__main__":
    main()
