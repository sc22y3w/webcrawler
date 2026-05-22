from __future__ import annotations

import json
from pathlib import Path

from src.search import ranked_search, suggest_queries


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "advanced_index.json"


def load_fixture_index() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_ranked_search_supports_boolean_operators_phrase_boosts_and_proximity():
    index = load_fixture_index()

    results = ranked_search(index, '"good friends"~1 AND good NOT bad OR gold')
    urls = [result["url"] for result in results]

    assert urls[0] == "https://quotes.toscrape.com/exact"
    assert "https://quotes.toscrape.com/proximity" in urls
    assert "https://quotes.toscrape.com/gold" in urls
    assert "https://quotes.toscrape.com/bad" not in urls


def test_suggest_queries_orders_suggestions_by_popularity():
    index = load_fixture_index()

    suggestions = suggest_queries(index, "go", limit=2)

    assert suggestions == ["good", "gold"]
