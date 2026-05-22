from __future__ import annotations

from dataclasses import dataclass
from math import log
import re
from typing import Any

from src.indexer import phrase_tokenize, stem, tokenize


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9']+")
QUERY_PATTERN = re.compile(
    r'"([^"]+)"(?:~(\d+))?|\b(AND|OR|NOT)\b|([A-Za-z0-9\']+)',
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class QueryAtom:
    kind: str
    terms: tuple[str, ...]
    raw: str
    slop: int = 0


def normalize_query_terms(query: str) -> list[str]:
    return tokenize(query)


def normalize_phrase_query_terms(query: str) -> list[str]:
    return phrase_tokenize(query)


def parse_advanced_query(query: str) -> list[dict[str, list[QueryAtom]]]:
    clauses: list[dict[str, list[QueryAtom]]] = []
    current_clause: dict[str, list[QueryAtom]] = {"positive": [], "negative": []}
    negate_next = False

    for match in QUERY_PATTERN.finditer(query):
        phrase, slop, operator, term = match.groups()
        if operator:
            keyword = operator.upper()
            if keyword == "OR":
                if current_clause["positive"] or current_clause["negative"]:
                    clauses.append(current_clause)
                current_clause = {"positive": [], "negative": []}
                negate_next = False
            elif keyword == "NOT":
                negate_next = True
            continue

        if phrase is not None:
            terms = tuple(normalize_phrase_query_terms(phrase))
            atom = QueryAtom(kind="phrase", terms=terms, raw=phrase, slop=int(slop or 0))
        else:
            terms = tuple(normalize_query_terms(term or ""))
            if not terms:
                continue
            atom = QueryAtom(kind="term", terms=terms, raw=term or "")

        if not atom.terms:
            continue

        target = current_clause["negative"] if negate_next else current_clause["positive"]
        target.append(atom)
        negate_next = False

    if current_clause["positive"] or current_clause["negative"] or not clauses:
        clauses.append(current_clause)

    return clauses


def phrase_in_tokens(phrase: list[str], tokens: list[str]) -> bool:
    if not phrase or len(phrase) > len(tokens):
        return False
    span = len(phrase)
    for start in range(len(tokens) - span + 1):
        if tokens[start : start + span] == phrase:
            return True
    return False


def phrase_with_slop(phrase: list[str], term_positions: dict[str, list[int]], slop: int) -> bool:
    if not phrase:
        return False
    if slop <= 0:
        return False

    positions = term_positions.get(phrase[0], [])
    if not positions:
        return False

    def match_from(index: int, previous_position: int, remaining_slop: int) -> bool:
        if index == len(phrase):
            return True

        next_positions = term_positions.get(phrase[index], [])
        lower_bound = previous_position + 1
        upper_bound = previous_position + remaining_slop + 1

        for position in next_positions:
            if position < lower_bound:
                continue
            if position > upper_bound:
                break
            gap = position - previous_position - 1
            if match_from(index + 1, position, remaining_slop - gap):
                return True
        return False

    for position in positions:
        if match_from(1, position, slop):
            return True
    return False


def distinct_query_terms_present(query_terms: list[str], tokens: list[str]) -> int:
    token_set = set(tokens)
    return sum(1 for term in set(query_terms) if term in token_set)


def _grouped_search(index: dict[str, Any], query: str) -> list[dict[str, Any]]:
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


def _inverse_document_frequency(index: dict[str, Any], term: str) -> float:
    pages = index.get("pages", [])
    if not pages:
        return 0.0
    document_frequency = len(index.get("postings", {}).get(term, {}))
    return log((1 + len(pages)) / (1 + document_frequency)) + 1.0


def _page_term_frequency(page: dict[str, Any], term: str) -> int:
    return len(page.get("term_positions", {}).get(term, []))


def _atom_matches_page(atom: QueryAtom, page: dict[str, Any], proximity_window: int) -> bool:
    if atom.kind == "term":
        return any(term in page.get("term_positions", {}) for term in atom.terms)
    if atom.slop > 0:
        return phrase_with_slop(list(atom.terms), page.get("term_positions", {}), atom.slop)
    return phrase_in_tokens(list(atom.terms), page.get("phrase_tokens", []))


def _score_clause(index: dict[str, Any], page: dict[str, Any], clause: dict[str, list[QueryAtom]], proximity_window: int) -> tuple[float, list[str], list[str]] | None:
    positive_atoms = clause["positive"]
    negative_atoms = clause["negative"]

    if positive_atoms and not all(_atom_matches_page(atom, page, proximity_window) for atom in positive_atoms):
        return None
    if any(_atom_matches_page(atom, page, proximity_window) for atom in negative_atoms):
        return None

    score = 0.0
    matched_terms: set[str] = set()
    matched_phrases: set[str] = set()

    for atom in positive_atoms:
        if atom.kind == "term":
            for term in atom.terms:
                matched_terms.add(term)
                if term in page.get("term_positions", {}):
                    frequency = _page_term_frequency(page, term)
                    score += (1.0 + log(frequency)) * _inverse_document_frequency(index, term)
        else:
            phrase_text = " ".join(atom.terms)
            matched_phrases.add(phrase_text)
            exact_phrase_match = phrase_in_tokens(list(atom.terms), page.get("phrase_tokens", []))
            if exact_phrase_match:
                score += 1.5 * len(atom.terms)
            score += 2.0 * len(atom.terms) / (atom.slop + 1)
            for term in atom.terms:
                if term in page.get("term_positions", {}):
                    score += 0.25 * _inverse_document_frequency(index, term)

    return score, sorted(matched_terms), sorted(matched_phrases)


def ranked_search(index: dict[str, Any], query: str, *, proximity_window: int = 3, limit: int | None = None) -> list[dict[str, Any]]:
    clauses = parse_advanced_query(query)
    if not clauses:
        return []

    ranked_results: list[dict[str, Any]] = []
    for page in index.get("pages", []):
        best_match: tuple[float, list[str], list[str]] | None = None
        for clause in clauses:
            clause_match = _score_clause(index, page, clause, proximity_window)
            if clause_match is None:
                continue
            if best_match is None or clause_match[0] > best_match[0]:
                best_match = clause_match

        if best_match is None or best_match[0] <= 0:
            continue

        score, matched_terms, matched_phrases = best_match
        ranked_results.append(
            {
                "url": page["url"],
                "title": page.get("title", ""),
                "score": round(score, 6),
                "matched_terms": matched_terms,
                "matched_phrases": matched_phrases,
            }
        )

    ranked_results.sort(key=lambda item: (-item["score"], item["url"]))
    if limit is not None:
        return ranked_results[:limit]
    return ranked_results


def suggest_queries(index: dict[str, Any], prefix: str, *, limit: int = 5) -> list[str]:
    normalized_prefix = " ".join(normalize_query_terms(prefix))
    if not normalized_prefix:
        return []

    postings = index.get("postings", {})
    candidates = [term for term in postings if term.startswith(normalized_prefix)]
    candidates.sort(key=lambda term: (-len(postings.get(term, {})), term))
    return candidates[:limit]


def search(
    index: dict[str, Any],
    query: str,
    *,
    ranking: str = "grouped",
    proximity_window: int = 3,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if ranking == "grouped":
        return _grouped_search(index, query)
    if ranking == "tfidf":
        return ranked_search(index, query, proximity_window=proximity_window, limit=limit)
    raise ValueError(f"Unsupported ranking mode: {ranking}")


def flatten_results(groups: list[dict[str, Any]]) -> list[str]:
    ordered_urls: list[str] = []
    for group in groups:
        ordered_urls.extend(group.get("pages", []))
    return ordered_urls
