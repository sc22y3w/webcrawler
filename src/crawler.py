from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable
from time import monotonic, sleep
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


DEFAULT_START_URL = "https://quotes.toscrape.com/"
DEFAULT_POLITENESS_WINDOW = 6.0


@dataclass(slots=True)
class CrawledPage:
    url: str
    title: str
    text: str
    links: list[str]


def normalize_url(url: str, base_url: str | None = None) -> str:
    resolved = urljoin(base_url or url, url)
    parsed = urlparse(resolved)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, ""))


def same_host(url: str, host: str) -> bool:
    return urlparse(url).netloc == host


def extract_links(html: str, base_url: str, host: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    discovered: list[str] = []
    for anchor in soup.find_all("a", href=True):
        absolute_url = normalize_url(anchor["href"], base_url)
        if same_host(absolute_url, host):
            discovered.append(absolute_url)
    return discovered


def extract_text_and_title(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = soup.get_text(" ", strip=True)
    return title, text


def crawl(
    start_url: str = DEFAULT_START_URL,
    *,
    max_pages: int | None = 50,
    politeness_window: float = DEFAULT_POLITENESS_WINDOW,
    session: requests.Session | None = None,
    progress_callback: Callable[[int, int | None, str], None] | None = None,
) -> list[CrawledPage]:
    session = session or requests.Session()
    host = urlparse(start_url).netloc
    queue: deque[str] = deque([normalize_url(start_url)])
    visited: set[str] = set()
    pages: list[CrawledPage] = []
    last_request_started_at: float | None = None

    while queue and (max_pages is None or len(pages) < max_pages):
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        now = monotonic()
        if last_request_started_at is not None:
            elapsed = now - last_request_started_at
            delay = politeness_window - elapsed
            if delay > 0:
                sleep(delay)

        last_request_started_at = monotonic()

        try:
            response = session.get(
                url,
                timeout=15,
                headers={"User-Agent": "webcrawler/1.0"},
            )
            response.raise_for_status()
        except requests.RequestException:
            continue

        title, text = extract_text_and_title(response.text)
        links = extract_links(response.text, url, host)
        pages.append(CrawledPage(url=url, title=title, text=text, links=links))

        if progress_callback is not None:
            progress_callback(len(pages), max_pages, url)

        for link in links:
            if link not in visited:
                queue.append(link)

    return pages
