from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any, Iterable

from src.crawler import CrawledPage


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9']+")
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "if",
        "in",
        "into",
        "is",
        "it",
        "no",
        "not",
        "of",
        "on",
        "or",
        "such",
        "that",
        "the",
        "their",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "was",
        "will",
        "with",
    }
)


@dataclass(slots=True)
class PageTokens:
    url: str
    title: str
    text: str
    tokens: list[str]
    phrase_tokens: list[str]
    term_positions: dict[str, list[int]]


def stem(word: str) -> str:
    for suffix in ("ingly", "edly", "ing", "edly", "edly", "ed", "ies", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            if suffix == "ies":
                return word[: -len(suffix)] + "y"
            return word[: -len(suffix)]
    return word


def tokenize(text: str, *, remove_stop_words: bool = True) -> list[str]:
    tokens: list[str] = []
    for raw_token in TOKEN_PATTERN.findall(text.lower()):
        if remove_stop_words and raw_token in STOP_WORDS:
            continue
        stemmed = stem(raw_token)
        if stemmed:
            tokens.append(stemmed)
    return tokens


def phrase_tokenize(text: str) -> list[str]:
    return tokenize(text, remove_stop_words=False)


def index_pages(pages: Iterable[CrawledPage]) -> dict[str, Any]:
    indexed_pages: list[dict[str, Any]] = []
    postings: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for page in pages:
        phrase_tokens = phrase_tokenize(f"{page.title} {page.text}")
        tokens = tokenize(f"{page.title} {page.text}")
        term_positions: dict[str, list[int]] = defaultdict(list)
        for position, token in enumerate(tokens):
            term_positions[token].append(position)

        indexed_pages.append(
            {
                "url": page.url,
                "title": page.title,
                "text": page.text,
                "tokens": tokens,
                "phrase_tokens": phrase_tokens,
                "term_positions": dict(term_positions),
            }
        )

        for token, positions in term_positions.items():
            postings[token][page.url] = {
                "frequency": len(positions),
                "positions": positions,
            }

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pages": indexed_pages,
        "postings": postings,
    }


def save_index(index: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2, ensure_ascii=False)
    return path


def load_index(input_path: str | Path) -> dict[str, Any]:
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
