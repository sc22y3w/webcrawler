## Webcrawler Search Tool

This project crawls `https://quotes.toscrape.com/`, builds an inverted index, saves it to disk, and lets you search the saved index.

## Project overview and purpose

This repository provides a compact end-to-end search pipeline for a small website.
Its goals are to:

- Crawl pages from `https://quotes.toscrape.com/` with a configurable politeness window (minimum 6 seconds between requests).
- Build and persist an inverted index for fast lookup.
- Expose an interactive CLI for building an index, loading it, searching it, and inspecting postings.
- Demonstrate core information-retrieval ideas such as token normalization, stemming, phrase matching, and optional TF-IDF ranking.

## Dependencies

Project dependencies are listed in `requirements.txt`.
Key packages include:

- `requests` for HTTP fetching.
- `beautifulsoup4` for HTML parsing.
- `pytest` for tests.
- `psutil` for benchmark memory metrics.

## Installation and setup

1. Clone the repository and open it in VS Code.
2. (Recommended) Create and activate a virtual environment.
3. Install dependencies from `requirements.txt`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Alternative (without creating a virtual environment)

```bash
pip install -r requirements.txt
```

## Usage

The CLI can run in two modes:

- Interactive mode: `python -m src.main`, then type commands at the prompt.
- Direct subcommand mode: `python -m src.main <subcommand> [options]`

The four core commands are `build`, `load`, `find`, and `print`.

### 1) `build`

Purpose: crawl the site and save a new index to disk.

Direct mode example:

```bash
python -m src.main build \
	--start-url https://quotes.toscrape.com/ \
	--max-pages 50 \
	--politeness-window 6 \
	--output data/index.json
```

Interactive mode example:

```text
python -m src.main
build
```

Notes:

- `--politeness-window` is configurable but enforced to a minimum of 6 seconds.
- Default output file is `data/index.json`.

### 2) `load`

Purpose: load an existing saved index into memory and show page count.

Direct mode example:

```bash
python -m src.main load --index data/index.json
```

Interactive mode example:

```text
python -m src.main
load
```

### 3) `find`

Purpose: search pages matching a query.

Direct mode examples:

```bash
python -m src.main find "good friends"
python -m src.main find --rank tfidf --proximity-window 1 --limit 5 '"good friends"~1 AND good NOT bad'
```

Interactive mode examples:

```text
python -m src.main
find good friends
find --rank tfidf "good friends"~1
```

### 4) `print`

Purpose: print the inverted-index postings entry for a word.

Direct mode example:

```bash
python -m src.main print nonsense
```

Interactive mode example:

```text
python -m src.main
print nonsense
```

### Additional command: `suggest`

Purpose: print query completion suggestions from indexed terms.

```bash
python -m src.main suggest --limit 5 go
```

## Testing instructions

Run all tests:

```bash
PYTHONPATH=. pytest -q
```

Run specific test modules:

```bash
PYTHONPATH=. pytest -q tests/test_crawler.py tests/test_main.py
```

## Benchmark instructions

Run the benchmark harness:

```bash
PYTHONPATH=. python benchmarks/run_benchmarks.py
```

## Notes

- Search is case-insensitive.
- Search results are grouped by relevance, with exact phrase matches shown before broader term matches.
- Ranked search mode uses a lightweight TF-IDF implementation with phrase boosts and supports boolean operators and proximity queries.

## Design notes

See [docs/SEARCH_DESIGN.md](docs/SEARCH_DESIGN.md) for query semantics and complexity notes.
See [RESEARCH.md](RESEARCH.md) for bibliography, workflow guidance, and demo notes.

