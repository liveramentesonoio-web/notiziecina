from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from news_monitor.config import FEED_SOURCES, FeedSource
from news_monitor.scoring import score_article
from news_monitor.text_utils import compact_text


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)

REQUEST_TIMEOUT = 12


def _entry_value(entry: Any, name: str, default: str = "") -> str:
    value = getattr(entry, name, default)
    if isinstance(value, str):
        return value
    return default


def _pick_feed_image(entry: Any) -> str | None:
    media_content = getattr(entry, "media_content", None) or []
    for item in media_content:
        url = item.get("url")
        if url:
            return url

    media_thumbnail = getattr(entry, "media_thumbnail", None) or []
    for item in media_thumbnail:
        url = item.get("url")
        if url:
            return url

    enclosures = getattr(entry, "enclosures", None) or []
    for item in enclosures:
        item_type = item.get("type", "")
        url = item.get("href")
        if url and item_type.startswith("image/"):
            return url

    return None


def _parse_published(entry: Any) -> str | None:
    published = _entry_value(entry, "published") or _entry_value(entry, "updated")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published).isoformat()
    except (TypeError, ValueError, IndexError):
        return published


def extract_article_details(link: str) -> tuple[str, str | None]:
    try:
        response = requests.get(
            link,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException:
        return "", None

    soup = BeautifulSoup(response.text, "html.parser")

    image_url = None
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = urljoin(link, og_image["content"])

    paragraphs = []
    for selector in [
        "article p",
        "[itemprop='articleBody'] p",
        ".article__body p",
        ".entry-content p",
        ".post-content p",
        "main p",
    ]:
        nodes = soup.select(selector)
        if nodes:
            paragraphs = [compact_text(node.get_text(" ", strip=True)) for node in nodes]
            break

    text = " ".join(part for part in paragraphs if part)
    return text[:12000], image_url


def fetch_source(
    source: FeedSource,
    *,
    enrich_articles: bool = True,
    enrichment_budget: int | None = None,
    known_links: set[str] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    parsed_feed = feedparser.parse(source.url)
    results: list[dict[str, Any]] = []
    enriched_count = 0

    for entry in parsed_feed.entries:
        title = compact_text(_entry_value(entry, "title"))
        summary = compact_text(_entry_value(entry, "summary") or _entry_value(entry, "description"))
        link = _entry_value(entry, "link")
        if not title or not link:
            continue
        if known_links and link in known_links:
            continue

        content_text = ""
        image_url = _pick_feed_image(entry)
        preview_score = score_article(title=title, summary=summary, content_text="")
        should_enrich = enrich_articles and (
            preview_score.score >= 8
            or bool(preview_score.chinese_hits)
            or bool(preview_score.crime_hits)
        )
        if enrichment_budget is not None and enriched_count >= enrichment_budget:
            should_enrich = False

        if should_enrich:
            extracted_text, extracted_image = extract_article_details(link)
            content_text = extracted_text
            image_url = image_url or extracted_image
            enriched_count += 1

        score = score_article(title=title, summary=summary, content_text=content_text)

        results.append(
            {
                "source_name": source.name,
                "source_region": source.region,
                "feed_url": source.url,
                "title": title,
                "link": link,
                "published": _parse_published(entry),
                "summary": summary,
                "content_text": content_text,
                "image_url": image_url,
                "score": score.score,
                "is_relevant": score.is_relevant,
                "matched_keywords": score.matched_keywords,
                "chinese_hits": score.chinese_hits,
                "crime_hits": score.crime_hits,
                "viral_hits": score.viral_hits,
            }
        )

    return results, enriched_count


def fetch_all_sources(
    *,
    enrich_articles: bool = True,
    max_enriched_articles: int = 40,
    known_links: set[str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    used_budget = 0
    for source in FEED_SOURCES:
        remaining_budget = None
        if enrich_articles:
            remaining_budget = max(max_enriched_articles - used_budget, 0)
        source_results, enriched_count = fetch_source(
            source,
            enrich_articles=enrich_articles,
            enrichment_budget=remaining_budget,
            known_links=known_links,
        )
        results.extend(source_results)
        used_budget += enriched_count
    return results
