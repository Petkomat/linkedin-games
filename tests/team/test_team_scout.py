"""The Scout: finds playable games on LinkedIn's games hub that are neither
built nor known, and files one task for each."""

from __future__ import annotations

from team.scout import HubGame, hub_games, new_games, scout

from .fakes import FakeGitHub


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


def test_a_hub_the_scout_cannot_read_is_one_incident():
    github = FakeGitHub()

    scout(github, "<html><body>Sign in to continue</body></html>", BUILT, rules, RUN)
    scout(github, "<html><body>Sign in to continue</body></html>", BUILT, rules, RUN)

    [incident] = github.open_issues()
    assert "kind:incident" in incident.labels
    assert "games hub" in incident.title
    assert len(github.comments_on(incident.number)) == 1
