"""The real browser for the tests in tests/play (skipped without the browser extra)."""

import pytest


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api", reason="needs: uv sync --extra browser")
    with sync_api.sync_playwright() as playwright:
        try:
            chrome = playwright.chromium.launch(channel="chrome")
        except sync_api.Error as error:
            pytest.skip(f"Playwright can't start Chrome: {error}")
        yield chrome
        chrome.close()
