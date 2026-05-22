from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.crawler import DEFAULT_START_URL, crawl
from src.indexer import index_pages, load_index, save_index
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


def interactive_cli() -> None:
    print("Webcrawler CLI")
    while True:
        try:
            command = input("Command (build/search/quit): ").strip().lower()
        except KeyboardInterrupt:
            print()
            return
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
        if command == "search":
            try:
                query = input("Search query: ").strip()
            except KeyboardInterrupt:
                print()
                continue
            search_command(
                argparse.Namespace(
                    index=DEFAULT_OUTPUT_PATH,
                    query=query,
                )
            )
            continue
        print("Please enter build, search, or quit.")


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
