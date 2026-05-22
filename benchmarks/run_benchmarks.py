"""Benchmark harness for the webcrawler project.

Measures:
- Indexing throughput (pages/sec)
- Query latency (ms) with p50/p95
- Peak memory during indexing (tracemalloc and optional psutil RSS)

Usage:
    PYTHONPATH=. python benchmarks/run_benchmarks.py [--synthetic N] [--iterations INT]

By default the script reads `data/index.json` as a representative dataset. Use
`--synthetic N` to generate N synthetic pages for larger stress tests.
"""
from __future__ import annotations

import json
import statistics
import time
import tracemalloc
from pathlib import Path
from typing import Any

from src.indexer import index_pages
from src.search import search
from src.crawler import CrawledPage

try:
    import psutil
except Exception:
    psutil = None

ROOT = Path(__file__).resolve().parents[1]
DATA_INDEX = ROOT / "data" / "index.json"


def load_pages_from_index(path: Path) -> list[CrawledPage]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    pages = []
    for p in data.get("pages", []):
        pages.append(CrawledPage(url=p.get("url", ""), title=p.get("title", ""), text=p.get("text", ""), links=[]))
    return pages


def generate_synthetic_pages(n: int, avg_tokens: int = 200) -> list[CrawledPage]:
    """Generate `n` synthetic pages with pseudo-random content.

    Content is deterministic for repeatability.
    """
    vocab = [f"word{i}" for i in range(1000)]
    pages: list[CrawledPage] = []
    for i in range(n):
        # deterministic pseudo-random content using simple arithmetic
        words = [vocab[(i * 31 + j * 17) % len(vocab)] for j in range(avg_tokens)]
        text = " ".join(words)
        title = f"Synthetic Page {i}"
        url = f"https://example.com/synth/{i}"
        pages.append(CrawledPage(url=url, title=title, text=text, links=[]))
    return pages


def bench_indexing(pages: list[CrawledPage], runs: int = 5) -> dict[str, Any]:
    times = []
    mem_peaks = []
    rss_peaks = []
    proc = psutil.Process() if psutil is not None else None
    for i in range(runs):
        tracemalloc.start()
        if proc is not None:
            rss_before = proc.memory_info().rss
        t0 = time.perf_counter()
        index = index_pages(pages)
        t1 = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        times.append(t1 - t0)
        mem_peaks.append(peak)
        if proc is not None:
            rss_after = proc.memory_info().rss
            rss_peaks.append(max(rss_before, rss_after))
    pages_count = len(pages)
    secs_mean = statistics.mean(times)
    return {
        "runs": runs,
        "pages": pages_count,
        "time_mean_s": secs_mean,
        "time_runs_s": times,
        "pages_per_second": pages_count / secs_mean if secs_mean > 0 else None,
        "mem_peak_bytes_mean": statistics.mean(mem_peaks) if mem_peaks else None,
        "rss_peak_bytes_mean": statistics.mean(rss_peaks) if rss_peaks else None,
    }


def bench_queries(index: dict[str, Any], queries: list[str], iterations: int = 200, *, ranking: str = "grouped") -> dict[str, Any]:
    results = {}
    # warmup
    for q in queries:
        search(index, q, ranking=ranking)

    for q in queries:
        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            _ = search(index, q, ranking=ranking)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000.0)
        times.sort()
        results[q] = {
            "iterations": iterations,
            "p50_ms": statistics.median(times),
            "p95_ms": times[int(0.95 * len(times)) - 1] if len(times) >= 20 else max(times),
            "mean_ms": statistics.mean(times),
        }
    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", type=int, default=0, help="Generate N synthetic pages instead of reading data/index.json")
    parser.add_argument("--iterations", type=int, default=200, help="Query iterations for latency measurement")
    parser.add_argument("--index-runs", type=int, default=5, help="Number of indexing runs to average")
    args = parser.parse_args()

    if args.synthetic and args.synthetic > 0:
        pages = generate_synthetic_pages(args.synthetic)
        print(f"Generated {len(pages)} synthetic pages")
    else:
        pages = load_pages_from_index(DATA_INDEX)
        print(f"Loaded {len(pages)} pages from {DATA_INDEX}")

    print("\nRunning indexing benchmark...")
    idx_bench = bench_indexing(pages, runs=args.index_runs)
    print(json.dumps(idx_bench, indent=2))

    # create an index once for query benchmarks
    index = index_pages(pages)

    queries = [
        "life",
        "albert einstein",
        "good novel",
        "miracle",
        "this term does not exist",
    ]

    print("\nRunning grouped query latency benchmark...")
    grouped_q_bench = bench_queries(index, queries, iterations=args.iterations, ranking="grouped")
    print(json.dumps(grouped_q_bench, indent=2))

    print("\nRunning TF-IDF query latency benchmark...")
    tfidf_q_bench = bench_queries(index, queries, iterations=args.iterations, ranking="tfidf")
    print(json.dumps(tfidf_q_bench, indent=2))

    out = {
        "indexing": idx_bench,
        "queries": {
            "grouped": grouped_q_bench,
            "tfidf": tfidf_q_bench,
        },
    }

    out_path = ROOT / "benchmarks" / "results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote results to {out_path}")


if __name__ == "__main__":
    main()
