from __future__ import annotations

from pathlib import Path

from src.crawler import CrawledPage
from src.indexer import index_pages, load_index, save_index, tokenize


def test_index_pages_records_tokens_and_positions(tmp_path: Path):
    pages = [
        CrawledPage(
            url="https://quotes.toscrape.com/a",
            title="A good friend",
            text="Good friends are good.",
            links=[],
        )
    ]

    index = index_pages(pages)
    output_path = save_index(index, tmp_path / "index.json")
    loaded = load_index(output_path)

    assert loaded["pages"][0]["url"] == "https://quotes.toscrape.com/a"
    assert loaded["postings"]["good"]["https://quotes.toscrape.com/a"]["frequency"] == 3
    assert loaded["postings"]["friend"]["https://quotes.toscrape.com/a"]["positions"] == [1, 3]
    assert tokenize("Good and friends") == ["good", "friend"]
