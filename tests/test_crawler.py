from __future__ import annotations

from types import SimpleNamespace

from src.crawler import crawl


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_crawl_enforces_politeness_window(monkeypatch):
    calls = []
    sleep_calls = []
    times = iter([0.0, 1.0, 1.0, 7.5, 7.5])

    def fake_monotonic():
        return next(times)

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    def fake_get(url, timeout, headers):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(
                """
                <html>
                    <head><title>One</title></head>
                    <body><a href="/two">Two</a></body>
                </html>
                """
            )
        return FakeResponse("<html><head><title>Two</title></head><body>Two page</body></html>")

    session = SimpleNamespace(get=fake_get)
    monkeypatch.setattr("src.crawler.monotonic", fake_monotonic)
    monkeypatch.setattr("src.crawler.sleep", fake_sleep)

    pages = crawl("https://quotes.toscrape.com/one", max_pages=2, politeness_window=6.0, session=session)

    assert [page.url for page in pages] == [
        "https://quotes.toscrape.com/one",
        "https://quotes.toscrape.com/two",
    ]
    assert sleep_calls == [6.0]


def test_crawl_does_not_sleep_when_delay_is_negative(monkeypatch):
    sleep_calls = []
    times = iter([0.0, 10.0, 10.0])

    def fake_monotonic():
        return next(times)

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    def fake_get(url, timeout, headers):
        return FakeResponse(
            """
            <html>
                <head><title>One</title></head>
                <body><a href="/two">Two</a></body>
            </html>
            """
        )

    session = SimpleNamespace(get=fake_get)
    monkeypatch.setattr("src.crawler.monotonic", fake_monotonic)
    monkeypatch.setattr("src.crawler.sleep", fake_sleep)

    pages = crawl("https://quotes.toscrape.com/one", max_pages=1, politeness_window=6.0, session=session)

    assert [page.url for page in pages] == ["https://quotes.toscrape.com/one"]
    assert sleep_calls == []
