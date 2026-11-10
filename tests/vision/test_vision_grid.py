import numpy as np
import pytest

from engines.vision import find_grid


def test_a_blank_screen_has_no_grid():
    # A page that is still loading: the player must see "no board yet", not crash.
    blank = np.full((600, 800, 3), 243, dtype=np.int16)

    with pytest.raises(ValueError, match="could not find a grid"):
        find_grid(blank)


def test_a_line_of_text_is_not_a_grid():
    # Evenly spaced letter strokes look like grid lines: a guest's "Start game"
    # screen was once read as a tiny board, and solved.
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (460, 120), "white")
    ImageDraw.Draw(image).text((40, 30), "Start game", fill="black", font=ImageFont.load_default(size=48))

    with pytest.raises(ValueError, match="could not find a grid"):
        find_grid(np.asarray(image, dtype=np.int16))
