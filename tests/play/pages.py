"""Local pages that stand in for LinkedIn in the browser tests."""

from __future__ import annotations

import base64
import html
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

# Like Mini Sudoku's guest view on GitHub's machines: an intro, then the start screen.
INTRO_SCREEN = """<span id='intro' style='position:fixed;left:20px;top:20px;font-size:24px'
  onclick="this.remove(); document.getElementById('start').style.display = 'inline'">Solve now</span>"""


def page_showing(
    browser,
    screenshot,
    behind_start_screen: bool = False,
    behind_intro: bool = False,
    screens_after_ms: int = 0,
    in_iframe: bool = False,
    blank_after_moves: int | None = None,
    back_after_ms: int | None = None,
):
    """A page that shows `screenshot` pixel for pixel and records input events.

    With `behind_start_screen`, the screenshot only shows after a click on
    "Start game"; with `behind_intro` too, that only shows after "Solve now".
    `screens_after_ms` delays the start screens, like a slow page, and
    `in_iframe` puts everything in an iframe, as LinkedIn does with Mini Sudoku.

    Like LinkedIn on its way to a result screen, the page goes blank once the
    screenshot has been pressed `blank_after_moves` times (once per click; a
    drag is one press), and shows the screenshot again `back_after_ms` later
    (never, if None)."""
    body, viewport = showing(
        screenshot, SCALE, behind_start_screen, behind_intro, screens_after_ms, in_iframe, blank_after_moves, back_after_ms
    )
    page = browser.new_page(device_scale_factor=SCALE, viewport=viewport)
    page.set_content(body)
    return page


def page_file(folder, screenshot, scale: float = 1, **screens) -> str:
    """The URL of a page like `page_showing`'s, saved in `folder`, for code that
    opens its own pages. It shows `screenshot` pixel for pixel on a screen with
    `scale` device pixels per page pixel (1 unless the browser is told otherwise)."""
    body, _ = showing(screenshot, scale, **screens)
    path = folder / f"{screenshot.stem}.html"
    path.write_text(body, encoding="utf-8")
    return path.as_uri()


def showing(
    screenshot,
    scale: float = SCALE,
    behind_start_screen: bool = False,
    behind_intro: bool = False,
    screens_after_ms: int = 0,
    in_iframe: bool = False,
    blank_after_moves: int | None = None,
    back_after_ms: int | None = None,
) -> tuple[str, dict]:
    """The HTML of a page showing `screenshot` pixel for pixel at `scale`, and
    the viewport it fills."""
    width, height = Image.open(screenshot).size
    mime = "jpeg" if screenshot.suffix == ".jpg" else "png"
    data = base64.b64encode(screenshot.read_bytes()).decode()
    hidden = "visibility:hidden;" if behind_start_screen else ""
    body = (
        # draggable=false: pressing on an image and moving would start the
        # browser's own drag-and-drop, which swallows the pointer events.
        f"<body style='margin:0'><img draggable='false' src='data:image/{mime};base64,{data}' "
        f"style='display:block;{hidden}width:{width / scale}px;height:{height / scale}px'>"
        f"{_later(_start_screens(behind_start_screen, behind_intro), screens_after_ms)}{RECORDER}"
        f"{_blank_at_the_end(blank_after_moves, back_after_ms)}</body>"
    )
    if in_iframe:
        body = (
            f"<body style='margin:0'><iframe srcdoc='{html.escape(body, quote=True)}' "
            "style='border:0;display:block;width:100vw;height:100vh'></iframe></body>"
        )
    return body, {"width": ceil(width / scale), "height": ceil(height / scale)}


def _start_screens(behind_start_screen: bool, behind_intro: bool) -> str:
    if behind_intro:
        return START_SCREEN.replace("<span id='start' style='", "<span id='start' style='display:none;") + INTRO_SCREEN
    return START_SCREEN if behind_start_screen else ""


def _blank_at_the_end(moves: int | None, back_after_ms: int | None) -> str:
    """A script that hides the screenshot after `moves` presses on it, and
    shows it again `back_after_ms` later (never, if None)."""
    if moves is None:
        return ""
    back = "" if back_after_ms is None else f"setTimeout(() => board.style.visibility = 'visible', {back_after_ms});"
    return f"""<script>
const board = document.querySelector("img");
let movesLeft = {moves};
board.addEventListener("pointerup", () => {{
  if (--movesLeft === 0) {{ board.style.visibility = "hidden"; {back} }}
}});
</script>"""


def _later(html: str, ms: int) -> str:
    """`html`, added to the page only after `ms` milliseconds."""
    if not ms or not html:
        return html
    quoted = html.replace("\\", "\\\\").replace("`", "\\`")
    return f"<script>setTimeout(() => document.body.insertAdjacentHTML('beforeend', `{quoted}`), {ms});</script>"
