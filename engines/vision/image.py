"""Loading screenshots."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ImageSource = str | Path | Image.Image  # a file path or an already opened image


def open_image(image: ImageSource) -> Image.Image:
    return image if isinstance(image, Image.Image) else Image.open(image)


def load_rgb(image: ImageSource) -> np.ndarray:
    """H x W x 3 int16 array (signed, so colour differences don't wrap)."""
    return np.asarray(open_image(image).convert("RGB"), dtype=np.int16)
