from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from src import main


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "advanced_index.json"


def load_fixture_index() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_find_command_supports_tfidf_ranking(monkeypatch, capsys, tmp_path: Path):
    index = load_fixture_index()
    monkeypatch.setattr(main, "load_index", lambda path: index)

    result = main.find_command(
        Namespace(
            index=tmp_path / "index.json",
            query='"good friends"~1',
            rank="tfidf",
            proximity_window=1,
            limit=2,
        )
    )

    captured = capsys.readouterr()

    assert result[0] == "https://quotes.toscrape.com/exact"
    assert "score=" in captured.out
    assert "https://quotes.toscrape.com/exact" in captured.out


def test_suggest_command_prints_query_suggestions(monkeypatch, capsys, tmp_path: Path):
    index = load_fixture_index()
    monkeypatch.setattr(main, "load_index", lambda path: index)

    result = main.suggest_command(
        Namespace(
            index=tmp_path / "index.json",
            limit=2,
            prefix=["go"],
        )
    )

    captured = capsys.readouterr()

    assert result == ["good", "gold"]
    assert "good" in captured.out
    assert "gold" in captured.out
