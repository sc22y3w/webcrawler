from __future__ import annotations

import argparse
import sys
import shlex
from typing import Any
from pathlib import Path

from src.crawler import DEFAULT_START_URL, crawl
from src.indexer import index_pages, load_index, save_index, tokenize
from src.search import flatten_results, search


DEFAULT_OUTPUT_PATH = Path("data") / "index.json"


def _render_build_progress(crawled_pages: int, max_pages: int | None, current_url: str) -> None:
    if max_pages is None:
        message = f"Scraping {crawled_pages} pages... {current_url}"
    else:
        bar_width = 20
        filled = min(bar_width, round(bar_width * crawled_pages / max_pages))
        bar = f"{'#' * filled}{'.' * (bar_width - filled)}"
        message = f"Scraping [{bar}] {crawled_pages}/{max_pages} pages {current_url}"
    print(f"\r{message}", end="", flush=True)


def build_command(args: argparse.Namespace) -> Path | None:
    try:
        _render_build_progress(0, args.max_pages, args.start_url)
        pages = crawl(
            start_url=args.start_url,
            max_pages=args.max_pages,
            politeness_window=args.politeness_window,
            progress_callback=_render_build_progress,
        )
    except KeyboardInterrupt:
        print()
        print("Build canceled.")
        return None

    print()
    index = index_pages(pages)
    output_path = save_index(index, args.output)
    print(f"Scraped {len(pages)} pages and saved the index to {output_path}")
    return output_path


def search_command(args: argparse.Namespace) -> list[str]:
    index = load_index(args.index)
    groups = search(index, args.query)
    ordered_urls = flatten_results(groups)
    for group in groups:
        print(f"{group['label']}: {', '.join(group['pages'])}")
    return ordered_urls


def load_command(args: argparse.Namespace) -> dict:
    index = load_index(args.index)
    page_count = len(index.get("pages", []))
    print(f"Loaded index with {page_count} pages from {args.index}")
    return index


def _print_postings(term: str, postings: dict[str, dict[str, Any]]) -> None:
    print(term)
    for url in sorted(postings):
        entry = postings[url]
        print(f"  {url}: frequency={entry['frequency']}, positions={entry['positions']}")


def print_index_command(args: argparse.Namespace) -> dict[str, Any] | None:
    index = load_index(args.index)
    terms = tokenize(args.word)
    if not terms:
        print(f"No printable index term found for {args.word!r}.")
        return None

    term = terms[0]
    postings = index.get("postings", {}).get(term)
    if not postings:
        print(f"No inverted index entry found for {term}.")
        return None

    _print_postings(term, postings)
    return postings


def interactive_cli() -> None:
    print("Webcrawler CLI")
    loaded_index: dict | None = None
    while True:
        try:
            raw_command = input("Command (build/load/search/print <word>/quit): ").strip()
        except KeyboardInterrupt:
            print()
            return
        if not raw_command:
            continue

        parts = shlex.split(raw_command)
        command = parts[0].lower()
        if command in {"quit", "exit", "q"}:
            return
        if command == "build":
            build_command(
                argparse.Namespace(
                    start_url=DEFAULT_START_URL,
                    output=DEFAULT_OUTPUT_PATH,
                    max_pages=50,
                    politeness_window=6.0,
                )
            )
            continue
        if command == "load":
            try:
                loaded_index = load_command(argparse.Namespace(index=DEFAULT_OUTPUT_PATH))
            except FileNotFoundError:
                print(f"No index found at {DEFAULT_OUTPUT_PATH}. Run build first.")
            continue
        if command == "search":
            try:
                query = input("Search query: ").strip()
            except KeyboardInterrupt:
                print()
                continue
            if loaded_index is None:
                try:
                    loaded_index = load_index(DEFAULT_OUTPUT_PATH)
                except FileNotFoundError:
                    print(f"No index found at {DEFAULT_OUTPUT_PATH}. Run build or load first.")
                    continue
            groups = search(loaded_index, query)
            ordered_urls = flatten_results(groups)
            for group in groups:
                print(f"{group['label']}: {', '.join(group['pages'])}")
            print(f"Matched {len(ordered_urls)} pages.")
            continue
        if command == "print":
            word = parts[1] if len(parts) > 1 else ""
            if not word:
                print("Usage: print <word>")
                continue
            if loaded_index is None:
                try:
                    loaded_index = load_index(DEFAULT_OUTPUT_PATH)
                except FileNotFoundError:
                    print(f"No index found at {DEFAULT_OUTPUT_PATH}. Run build or load first.")
                    continue
            terms = tokenize(word)
            if not terms:
                print(f"No printable index term found for {word!r}.")
                continue
            term = terms[0]
            postings = loaded_index.get("postings", {}).get(term)
            if not postings:
                print(f"No inverted index entry found for {term}.")
                continue
            _print_postings(term, postings)
            continue
        print("Please enter build, load, search, print <word>, or quit.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and search the quotes.toscrape.com index.")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="Crawl the target website and save an index.")
    build_parser.add_argument("--start-url", default=DEFAULT_START_URL)
    build_parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH)
    build_parser.add_argument("--max-pages", type=int, default=50)
    build_parser.add_argument("--politeness-window", type=float, default=6.0)
    build_parser.set_defaults(func=build_command)

    search_parser = subparsers.add_parser("search", help="Search a saved index.")
    search_parser.add_argument("--index", default=DEFAULT_OUTPUT_PATH)
    search_parser.add_argument("query")
    search_parser.set_defaults(func=search_command)

    load_parser = subparsers.add_parser("load", help="Load a saved index.")
    load_parser.add_argument("--index", default=DEFAULT_OUTPUT_PATH)
    load_parser.set_defaults(func=load_command)

    print_parser = subparsers.add_parser("print", help="Print the inverted index entry for a word.")
    print_parser.add_argument("--index", default=DEFAULT_OUTPUT_PATH)
    print_parser.add_argument("word")
    print_parser.set_defaults(func=print_index_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        interactive_cli()
        return 0

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        interactive_cli()
        return 0
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
