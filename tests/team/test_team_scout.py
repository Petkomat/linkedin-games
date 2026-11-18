"""The Scout: finds playable games on LinkedIn's games hub that are neither
built nor known, and files one task for each."""

from __future__ import annotations

from team.scout import HubGame, how_to_play, hub_games, new_games, rules_lines, scout, wait_for_rules

from .fakes import FakeGitHub

# The Sumbreak dialog of run 44283221256, read 4 s after it opened (#14).
SUMBREAK = "How to play Sumbreak\n\nDrag to combine matching neighbor cells. Repeat until one cell remains.\n\nPlay game\n0 notifications"
SUMBREAK_RULES = ["How to play Sumbreak", "Drag to combine matching neighbor cells. Repeat until one cell remains."]


def card(name: str, slug: str) -> str:
    return (
        f'<li class="pb-1"><a class="game-entrypoint-card" href="https://www.linkedin.com/games/{slug}/?trk=games_hub">'
        f'<img class="game-entrypoint-card__bg-img" alt="{name}"><p class="font-semibold">{name}</p>'
        f'<div class="game-entrypoint-card__insight"><span>Played by many</span></div></a></li>'
    )


def hub(*games: tuple[str, str]) -> str:
    cards = "".join(card(name, slug) for name, slug in games)
    return f'<html><body><main><div class="game-hub__container"><ul class="list-style-none">{cards}</ul></div></main></body></html>'


TODAY = hub(("Wend", "wend"), ("Mini Sudoku", "mini-sudoku"), ("Pinpoint", "pinpoint"), ("Sumbreak", "sumbreak"))
BUILT = {"wend", "mini-sudoku"}
RUN = "https://github.com/owner/linkedin-games/actions/runs/42"


def rules(game: HubGame) -> str:
    return f"How to play {game.name}: make every row sum up."


class Clock:
    """A clock that only moves when the code under test sleeps."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class Dialog:
    """A dialog whose text, read once per call, goes through `texts` and then stays at the last."""

    def __init__(self, *texts: str) -> None:
        self.texts, self.reads = list(texts), 0

    def __call__(self) -> str:
        self.reads += 1
        return self.texts[min(self.reads, len(self.texts)) - 1]


def test_the_hub_lists_each_game_with_its_name_and_address():
    assert hub_games(TODAY) == [
        HubGame("Wend", "wend"),
        HubGame("Mini Sudoku", "mini-sudoku"),
        HubGame("Pinpoint", "pinpoint"),
        HubGame("Sumbreak", "sumbreak"),
    ]


def test_new_games_are_the_ones_neither_built_nor_known():
    assert new_games(hub_games(TODAY), built=BUILT, known={"pinpoint"}) == [HubGame("Sumbreak", "sumbreak")]


def test_a_new_game_gets_one_task_with_its_rules_and_board():
    github = FakeGitHub()
    github.create_issue("New game: Pinpoint", "Declined.\n\n<!-- scout {\"slug\": \"pinpoint\"} -->", {"kind:new-game", "declined"})
    github.close(1, not_planned=True)

    [number] = scout(github, TODAY, BUILT, rules, RUN)

    issue = github.issues[number]
    assert issue.title == "New game: Sumbreak"
    assert issue.labels == {"kind:new-game"}
    assert "How to play Sumbreak" in issue.body
    assert "https://www.linkedin.com/games/sumbreak/" in issue.body
    assert RUN in issue.body
    assert scout(github, TODAY, BUILT, rules, RUN) == []


def test_the_rules_are_the_dialogs_heading_and_sentences_without_its_button_or_screen_reader_lines():
    assert rules_lines(SUMBREAK) == SUMBREAK_RULES


def test_rules_over_several_lines_keep_their_order_and_lose_every_screen_reader_line_and_button():
    dialog = (
        "Dialog content start.\n"
        "How to play Zip\n"
        "Close\n\n"
        "Connect the dots in order.\n"
        "1 notification\n"
        "  Fill  every cell.  \n"
        "12 notifications\n"
        "Got it\n"
        "START GAME\n"
        "Dialog content end."
    )

    assert rules_lines(dialog) == ["How to play Zip", "Connect the dots in order.", "Fill every cell."]


def test_a_dialog_with_nothing_but_its_heading_has_no_rules():
    assert rules_lines("How to play Sumbreak\n0 notifications") == []
    assert rules_lines("Dialog content start.\nHow to play Sumbreak\n\nPlay game\nDialog content end.") == []
    assert rules_lines("") == []


def test_the_new_game_task_quotes_the_rules_a_line_to_a_paragraph():
    assert how_to_play(SUMBREAK) == (
        "## How to play, as LinkedIn shows a guest\n\n"
        "> How to play Sumbreak\n"
        ">\n"
        "> Drag to combine matching neighbor cells. Repeat until one cell remains."
    )


def test_the_new_game_task_says_so_when_the_dialog_had_no_rules():
    couldnt = "The Scout couldn't read the rules. Open the game as a guest and click its ? button."

    assert how_to_play("How to play Sumbreak\n0 notifications") == couldnt
    assert how_to_play("") == couldnt


def test_the_scout_reads_the_dialog_once_its_rules_have_arrived_and_stopped_changing():
    shell = "How to play Sumbreak\n0 notifications"
    clock = Clock()
    dialog = Dialog(shell, shell, shell, shell, "How to play Sumbreak\n\nDrag to combine", SUMBREAK)

    assert wait_for_rules(dialog, 15.0, clock, clock.sleep) == SUMBREAK
    assert clock.now < 6.0  # it didn't wait out the limit once the text was still


def test_a_dialog_that_keeps_changing_is_read_as_it_is_at_the_time_limit():
    clock = Clock()
    seen = []

    def read() -> str:
        seen.append(f"How to play Sumbreak\nRule {len(seen) + 1}.")
        return seen[-1]

    assert wait_for_rules(read, 15.0, clock, clock.sleep) == seen[-1]
    assert 14.0 <= clock.now <= 15.0


def test_a_dialog_that_never_shows_its_rules_is_waited_for_until_the_time_limit():
    clock = Clock()

    text = wait_for_rules(Dialog("How to play Sumbreak\n0 notifications"), 15.0, clock, clock.sleep)

    assert 14.0 <= clock.now <= 15.0
    assert how_to_play(text).startswith("The Scout couldn't read the rules.")


def test_a_hub_the_scout_cannot_read_is_one_incident():
    github = FakeGitHub()

    scout(github, "<html><body>Sign in to continue</body></html>", BUILT, rules, RUN)
    scout(github, "<html><body>Sign in to continue</body></html>", BUILT, rules, RUN)

    [incident] = github.open_issues()
    assert "kind:incident" in incident.labels
    assert "games hub" in incident.title
    assert len(github.comments_on(incident.number)) == 1
