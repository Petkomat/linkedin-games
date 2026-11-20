import numpy as np

from engines.vision import split_glyphs

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
