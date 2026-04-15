from dataclasses import dataclass
import re
from typing import Iterable

from news_monitor.config import (
    CHINESE_KEYWORDS,
    CRIME_AND_ENFORCEMENT_KEYWORDS,
    VIRAL_ATTENTION_KEYWORDS,
)
from news_monitor.text_utils import normalize_text


@dataclass
class ScoreResult:
    score: int
    chinese_hits: list[str]
    crime_hits: list[str]
    viral_hits: list[str]
    matched_keywords: list[str]
    is_relevant: bool


def _find_hits(text: str, keywords: Iterable[str]) -> list[str]:
    hits: list[str] = []
    for keyword in keywords:
        needle = normalize_text(keyword)
        if not needle:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(needle)}(?!\w)")
        if pattern.search(text):
            hits.append(keyword)
    return hits


def score_article(*, title: str, summary: str, content_text: str) -> ScoreResult:
    merged = normalize_text(" ".join(part for part in [title, summary, content_text] if part))
    title_text = normalize_text(title)

    chinese_hits = _find_hits(merged, CHINESE_KEYWORDS)
    crime_hits = _find_hits(merged, CRIME_AND_ENFORCEMENT_KEYWORDS)
    viral_hits = _find_hits(merged, VIRAL_ATTENTION_KEYWORDS)

    score = 0
    score += len(chinese_hits) * 5
    score += len(crime_hits) * 4
    score += len(viral_hits) * 2

    if chinese_hits and crime_hits:
        score += 12

    if _find_hits(title_text, CHINESE_KEYWORDS):
        score += 5

    if _find_hits(title_text, CRIME_AND_ENFORCEMENT_KEYWORDS):
        score += 4

    if "prato" in merged:
        score += 3

    if "roma" in merged or "milano" in merged:
        score += 1

    is_relevant = bool(chinese_hits and crime_hits)
    if is_relevant and score < 20:
        score = 20

    matched_keywords = sorted(set(chinese_hits + crime_hits + viral_hits))

    return ScoreResult(
        score=score,
        chinese_hits=chinese_hits,
        crime_hits=crime_hits,
        viral_hits=viral_hits,
        matched_keywords=matched_keywords,
        is_relevant=is_relevant,
    )
