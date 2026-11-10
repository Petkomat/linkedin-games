"""Local pages that stand in for LinkedIn in the browser tests."""

from __future__ import annotations

import base64
from math import ceil

from PIL import Image

SCALE = 2  # a high-resolution screen: two screenshot pixels per page pixel

RECORDER = """<script>
window.events = [];
for (const type of ["pointerdown", "pointermove", "pointerup"]) {
  addEventListener(type, (e) => {
    if (type !== "pointermove" || e.buttons) events.push({type, x: e.clientX, y: e.clientY, t: e.timeStamp});
  });
}
addEventListener("keydown", (e) => events.push({type: "keydown", key: e.key}));
</script>"""

# Like LinkedIn's guest view: a "Start game" button that reveals the board.
START_SCREEN = """<span id='start' style='position:fixed;left:20px;top:20px;font-size:24px'
  onclick="this.remove(); document.querySelector('img').style.visibility = 'visible'">Start game</span>"""


def page_showing(browser, screenshot, behind_start_screen: bool = False):
    """A page that shows `screenshot` pixel for pixel and records input events.

    With `behind_start_screen`, the screenshot only shows after a click on
    "Start game"."""
    width, height = Image.open(screenshot).size
    page = browser.new_page(
        device_scale_factor=SCALE,
        viewport={"width": ceil(width / SCALE), "height": ceil(height / SCALE)},
    )
    mime = "jpeg" if screenshot.suffix == ".jpg" else "png"
    data = base64.b64encode(screenshot.read_bytes()).decode()
    hidden = "visibility:hidden;" if behind_start_screen else ""
    page.set_content(
        # draggable=false: pressing on an image and moving would start the
        # browser's own drag-and-drop, which swallows the pointer events.
        f"<body style='margin:0'><img draggable='false' src='data:image/{mime};base64,{data}' "
        f"style='display:block;{hidden}width:{width / SCALE}px;height:{height / SCALE}px'>"
        f"{START_SCREEN if behind_start_screen else ''}{RECORDER}</body>"
    )
    return page
