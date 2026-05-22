from __future__ import annotations

from src.crawler import CrawledPage
from src.indexer import index_pages
from src.search import search


def test_search_groups_phrase_matches_before_term_matches():
    pages = [
        CrawledPage(
            url="https://quotes.toscrape.com/polar-bears-are-cool",
            title="Polar bears are cool",
            text="Polar bears are cool.",
            links=[],
        ),
        CrawledPage(
            url="https://quotes.toscrape.com/polar-bears",
            title="Polar bears",
            text="Polar bears are amazing creatures.",
            links=[],
        ),
        CrawledPage(
            url="https://quotes.toscrape.com/facts",
            title="Cool facts",
            text="Polar myths about bears and cool stories.",
            links=[],
        ),
    ]

    index = index_pages(pages)
    groups = search(index, "polar bears are cool")

    assert groups[0]["kind"] == "phrase"
    assert groups[0]["label"] == "polar bears are cool"
    assert groups[0]["pages"] == ["https://quotes.toscrape.com/polar-bears-are-cool"]
    assert any(group["kind"] == "terms" for group in groups)
    terms_group = next(group for group in groups if group["kind"] == "terms")
    assert "https://quotes.toscrape.com/facts" in terms_group["pages"]
