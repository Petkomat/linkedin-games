"""Read printed characters: numbers on badges, capital letters on tiles.

Each glyph's HOG descriptor (a histogram of gradient directions per zone) is
compared with templates of the characters it could be. The templates are
rendered from Pillow's bundled font at several stroke weights, so they don't
depend on any fonts being installed. Gradient directions are less sensitive to
stroke weight and font than raw pixels are.

Before comparing, the candidates are narrowed to characters with the glyph's
number of holes (8 and B have two; 0, 6, 9, A, D, O, P, Q, R and sometimes 4
have one), which holds in any plain font. That alone separates most of the
usual mix-ups (3/8, 9/8, 5/6, O/C).
"""

from __future__ import annotations

from functools import cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .morphology import bbox, count_holes

DIGITS = "0123456789"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
HOLES = {
    "0": {1}, "1": {0}, "2": {0}, "3": {0}, "4": {0, 1},
    "5": {0}, "6": {1}, "7": {0}, "8": {2}, "9": {1},
    **{letter: {0} for letter in LETTERS},
    "A": {1}, "B": {2}, "D": {1}, "O": {1}, "P": {1}, "Q": {1}, "R": {1},
}  # fmt: skip
SIDE, ZONES, BINS = 32, 4, 8  # descriptor: SIDExSIDE glyph, ZONESxZONES zones, BINS directions
STROKE_WEIGHTS = (0, 2, 4, 6)


def read_number(ink: np.ndarray) -> int | None:
    """`ink` is a 0..1 map of digit pixels; returns the number or None if blank."""
    glyphs = _split_glyphs(ink)
    if not glyphs:
        return None
    return int("".join(_classify(glyph, DIGITS) for glyph in glyphs))


def read_letter(ink: np.ndarray) -> str | None:
    """`ink` is a 0..1 map of one capital letter's pixels; returns it or None if blank."""
    solid = ink > 0.5
    if not solid.any():
        return None
    return _classify(ink[bbox(solid)], LETTERS)


def _split_glyphs(ink: np.ndarray) -> list[np.ndarray]:
    """Cut the ink into glyphs at empty columns, dropping specks."""
    solid = ink > 0.5
    columns = np.flatnonzero(solid.any(axis=0))
    if columns.size == 0:
        return []
    runs = np.split(columns, np.flatnonzero(np.diff(columns) > 1) + 1)
    glyphs = [ink[:, run[0] : run[-1] + 1] for run in runs]
    glyphs = [g[bbox(g > 0.5)] for g in glyphs]
    tallest = max(g.shape[0] for g in glyphs)
    return [g for g in glyphs if g.shape[0] >= 0.6 * tallest]


def _classify(glyph: np.ndarray, alphabet: str) -> str:
    holes = count_holes(glyph > 0.5, min_area=max(2, round(0.02 * glyph.size)))
    allowed = [ch for ch in alphabet if holes in HOLES[ch]] or list(alphabet)
    descriptor = _hog(glyph)
    _, best = max(
        (float(descriptor @ template), ch) for ch, template in _templates(alphabet) if ch in allowed
    )
    return best


@cache
def _templates(alphabet: str) -> tuple[tuple[str, np.ndarray], ...]:
    size = 64
    font = ImageFont.load_default(size=size)
    out = []
    for ch in alphabet:
        for weight in STROKE_WEIGHTS:
            canvas = Image.new("L", (3 * size, 3 * size), 0)
            ImageDraw.Draw(canvas).text(
                (size // 2, size // 4), ch, fill=255, font=font,
                stroke_width=weight, stroke_fill=255,
            )
            ink = np.asarray(canvas, dtype=float) / 255
            out.append((ch, _hog(ink[bbox(ink > 0.5)])))
    return tuple(out)


def _hog(glyph: np.ndarray) -> np.ndarray:
    """Unit-length histogram of gradient directions over ZONES x ZONES zones."""
    h, w = glyph.shape
    side = max(h, w)  # pad to a square so the aspect ratio is kept ("1" is narrow)
    square = np.zeros((side, side))
    square[(side - h) // 2 : (side - h) // 2 + h, (side - w) // 2 : (side - w) // 2 + w] = glyph
    image = Image.fromarray((square * 255).astype(np.uint8)).resize((SIDE, SIDE), Image.BOX)
    pixels = np.asarray(image.filter(ImageFilter.GaussianBlur(1)), dtype=float) / 255

    gy, gx = np.gradient(pixels)
    magnitude = np.hypot(gx, gy)
    direction = (np.arctan2(gy, gx) % (2 * np.pi)) / (2 * np.pi) * BINS
    lower = np.floor(direction).astype(int) % BINS
    upper_share = direction - np.floor(direction)

    zone = SIDE // ZONES
    features = np.zeros((ZONES, ZONES, BINS))
    for i in range(ZONES):
        for j in range(ZONES):
            cut = (slice(i * zone, (i + 1) * zone), slice(j * zone, (j + 1) * zone))
            m, b, s = magnitude[cut].ravel(), lower[cut].ravel(), upper_share[cut].ravel()
            np.add.at(features[i, j], b, m * (1 - s))
            np.add.at(features[i, j], (b + 1) % BINS, m * s)
    vector = features.ravel()
    return vector / (np.linalg.norm(vector) + 1e-9)
