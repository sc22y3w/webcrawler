from __future__ import annotations

import re
from typing import Any

from src.indexer import stem, tokenize, phrase_tokenize


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9']+")


def normalize_query_terms(query: str) -> list[str]:
    return tokenize(query)


def normalize_phrase_query_terms(query: str) -> list[str]:
    return phrase_tokenize(query)


def phrase_in_tokens(phrase: list[str], tokens: list[str]) -> bool:
    if not phrase or len(phrase) > len(tokens):
        return False
    span = len(phrase)
    for start in range(len(tokens) - span + 1):
        if tokens[start : start + span] == phrase:
            return True
    return False


def distinct_query_terms_present(query_terms: list[str], tokens: list[str]) -> int:
    token_set = set(tokens)
    return sum(1 for term in set(query_terms) if term in token_set)


def search(index: dict[str, Any], query: str) -> list[dict[str, Any]]:
    query_terms = normalize_query_terms(query)
    raw_query_terms = TOKEN_PATTERN.findall(query.lower())

    if not query_terms and not raw_query_terms:
        return []

    pages = index.get("pages", [])
    assigned_pages: set[str] = set()
    groups: list[dict[str, Any]] = []

    for phrase_length in range(len(raw_query_terms), 1, -1):
        for start in range(0, len(raw_query_terms) - phrase_length + 1):
            phrase = raw_query_terms[start : start + phrase_length]
            normalized_phrase = [stem(term) for term in phrase]
            matching_urls = [
                page["url"]
                for page in pages
                if page["url"] not in assigned_pages
                and phrase_in_tokens(normalized_phrase, page.get("phrase_tokens", []))
            ]
            if matching_urls:
                matching_urls.sort()
                groups.append(
                    {
                        "kind": "phrase",
                        "label": " ".join(phrase),
                        "pages": matching_urls,
                    }
                )
                assigned_pages.update(matching_urls)

    total_terms = len(set(query_terms))
    for distinct_count in range(total_terms, 0, -1):
        matching_urls = [
            page["url"]
            for page in pages
            if page["url"] not in assigned_pages
            and distinct_query_terms_present(query_terms, page.get("tokens", [])) >= distinct_count
        ]
        if matching_urls:
            matching_urls.sort()
            groups.append(
                {
                    "kind": "terms",
                    "label": f"{distinct_count} terms",
                    "pages": matching_urls,
                }
            )
            assigned_pages.update(matching_urls)

    return groups


def flatten_results(groups: list[dict[str, Any]]) -> list[str]:
    ordered_urls: list[str] = []
    for group in groups:
        ordered_urls.extend(group.get("pages", []))
    return ordered_urls
