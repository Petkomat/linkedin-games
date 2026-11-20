import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from engines.vision import Unreadable, read_letter, read_number, split_glyphs


def printed(text: str, size: int) -> np.ndarray:
    """`text` printed in Pillow's font, `size` px, as a 0..1 map of its ink."""
    font = ImageFont.load_default(size=size)
    canvas = Image.new("L", (size * (len(text) + 2), 2 * size), 0)
    ImageDraw.Draw(canvas).text((size // 2, size // 4), text, fill=255, font=font)
    return np.asarray(canvas, dtype=float) / 255


@pytest.mark.parametrize("size", [14, 20, 40])
def test_reads_numbers_and_letters(size):
    assert read_number(printed("1024", size)) == 1024
    assert read_number(printed("3579", size)) == 3579
    assert read_number(printed("68", size)) == 68
    assert read_letter(printed("R", size)) == "R"
    assert read_letter(printed("W", size)) == "W"


@pytest.mark.parametrize("size", [14, 20, 40])
@pytest.mark.parametrize("sign", ["+", "=", "%", "<"])
def test_a_sign_that_is_no_digit_is_refused_not_read_as_the_nearest_digit(sign, size):
    with pytest.raises(Unreadable):
        read_number(printed(sign, size))


@pytest.mark.parametrize("size", [14, 20, 40])
def test_a_number_with_a_sign_among_its_digits_is_refused(size):
    with pytest.raises(Unreadable):
        read_number(printed("1+2", size))


@pytest.mark.parametrize("size", [14, 20, 40])
@pytest.mark.parametrize("sign", ["=", "-", "%"])
def test_a_sign_that_is_no_letter_is_refused_not_read_as_the_nearest_letter(sign, size):
    with pytest.raises(Unreadable):
        read_letter(printed(sign, size))


def test_reads_a_1_with_a_slab_foot():
    # The ink of a 1 on sumbreak2.png, where LinkedIn draws tiles as circles:
    # small, and with a foot that Pillow's 1 hasn't got.
    one = np.array(
        [
            [ch == "#" for ch in row]
            for row in """
            .####....
            #####....
            ...##....
            ...##....
            ...##....
            ...##....
            ...##....
            ...##....
            ...##....
            ...##....
            ...##....
            ...##....
            .#######.
            #########
            """.split()
        ],
        dtype=float,
    )

    assert read_number(one) == 1


def test_a_refusal_is_a_value_error_the_games_already_treat_as_no_board():
    assert issubclass(Unreadable, ValueError)


def test_blank_ink_is_still_no_number_and_no_letter():
    assert read_number(np.zeros((20, 20))) is None
    assert read_letter(np.zeros((20, 20))) is None

# Ink 12 rows high: a glyph 10 tall in columns 2-3, a mark 5 tall in columns
# 6-8 (as the x of a x2 is beside its 2), a speck in column 11, and another
# glyph 10 tall in columns 14-15.
INK = np.zeros((12, 18), dtype=bool)
INK[1:11, 2:4] = True
INK[4:9, 6:9] = True
INK[6, 11] = True
INK[1:11, 14:16] = True


def test_cuts_ink_into_glyphs_at_empty_columns_left_to_right_each_cut_to_its_box():
    glyphs = split_glyphs(INK, speck=0.3)

    assert [left for left, _ in glyphs] == [2, 6, 14]
    assert [glyph.shape for _, glyph in glyphs] == [(10, 2), (5, 3), (10, 2)]
    assert all(glyph.all() for _, glyph in glyphs)


def test_drops_glyphs_shorter_than_a_share_of_the_tallest():
    # Digits are as tall as each other; by default anything under 0.6 of them goes.
    assert [left for left, _ in split_glyphs(INK)] == [2, 14]


def test_no_ink_is_no_glyphs():
    assert split_glyphs(np.zeros((5, 5))) == []
