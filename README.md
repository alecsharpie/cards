# Cards

A deck of SVG playing cards and a physics card table to play with them.

**Play:** https://www.alecsharpie.me/cards/

- `index.html` — the table. Every card is a 3D rigid body: gravity, corner
  contacts with friction on the felt, air drag, and a kinematic hand while you
  hold it. Pull to slide, push an edge inward to lift and flip, let go mid-lift
  to throw, tap to flip a card away from you.
- `generate.py` — writes the 52 cards, two jokers and a back as standalone SVGs
  into `deck/`, plus `deck/preview.html`. No dependencies beyond Python 3.

```
python3 generate.py
```
