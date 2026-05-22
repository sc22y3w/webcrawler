# Search Design

## Overview
The repository uses a classic crawl -> tokenize -> inverted index -> query pipeline for `quotes.toscrape.com`.

The default search path keeps the existing grouped relevance behavior:
- exact phrase groups first
- then progressively shorter phrase substrings
- then term-coverage groups

A ranked search mode is also available for advanced queries. It supports:
- boolean operators: `AND`, `OR`, `NOT`
- quoted phrases
- proximity queries such as `"good friends"~1`
- TF-IDF ranking with phrase boosts
- query suggestions via prefix lookup

## Public API
- `src.search.search(index, query, ranking="grouped")`
- `src.search.ranked_search(index, query, proximity_window=3, limit=None)`
- `src.search.suggest_queries(index, prefix, limit=5)`

## Complexity
Let:
- $P$ be the number of indexed pages
- $T$ be the total number of tokens across all pages
- $Q$ be the number of query atoms
- $L$ be the length of a phrase query

Then:
- Crawl time is dominated by HTTP requests and is roughly $O(P + E)$ for page/link traversal, excluding network latency.
- Index construction is $O(T)$ time and $O(T)$ space for tokens and postings.
- Grouped search is approximately $O(P \cdot Q)$ for term coverage checks, plus phrase scans.
- Ranked search is approximately $O(P \cdot Q)$ for clause checks, with proximity matching depending on the number of stored term positions.
- Suggestions are $O(V)$ over vocabulary size, with a small sort for the matching prefix bucket.

## Benchmarking
Use `PYTHONPATH=. python benchmarks/run_benchmarks.py` to measure:
- indexing throughput
- grouped query latency p50/p95
- TF-IDF query latency p50/p95
- peak memory during indexing

The benchmark harness writes results to `benchmarks/results.json`.
