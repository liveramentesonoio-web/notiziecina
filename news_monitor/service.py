from __future__ import annotations

from dataclasses import dataclass

from news_monitor.database import (
    get_connection,
    get_known_links,
    save_rewrite,
    save_translation,
    upsert_article,
)
from news_monitor.fetcher import fetch_all_sources
from news_monitor.translator import (
    RewriteResult,
    TranslationResult,
    has_translation_api_key,
    rewrite_article_for_engagement,
    translate_article_to_chinese,
)


@dataclass
class RefreshResult:
    inserted_or_updated: int
    skipped_existing: int
    relevant_count: int
    translated_count: int
    rewritten_count: int
    total_count: int


def translate_article(article_row) -> TranslationResult:
    result = translate_article_to_chinese(
        title=article_row["title"],
        published=article_row["published"] or "",
        summary=article_row["summary"] or "",
        content_text=article_row["content_text"] or article_row["summary"] or article_row["title"],
    )
    connection = get_connection()
    try:
        save_translation(
            connection,
            article_id=article_row["id"],
            translated_title=result.translated_title,
            translated_summary=result.translated_summary,
            translated_content=result.translated_content,
            translated_published=result.translated_published,
            translated_model=result.model,
        )
        connection.commit()
    finally:
        connection.close()
    return result


def rewrite_article(article_row, *, target_length: int = 90) -> RewriteResult:
    result = rewrite_article_for_engagement(
        title=article_row["title"],
        published=article_row["published"] or "",
        summary=article_row["summary"] or "",
        content_text=article_row["content_text"] or article_row["summary"] or article_row["title"],
        translated_title=article_row["translated_title"] or "",
        translated_summary=article_row["translated_summary"] or "",
        translated_content=article_row["translated_content"] or "",
        target_length=target_length,
    )
    connection = get_connection()
    try:
        save_rewrite(
            connection,
            article_id=article_row["id"],
            rewritten_title=result.rewritten_title,
            rewritten_summary=result.rewritten_summary,
            rewritten_model=result.model,
        )
        connection.commit()
    finally:
        connection.close()
    return result


def refresh_articles(
    *,
    enrich_articles: bool = True,
    max_enriched_articles: int = 40,
    auto_translate: bool = True,
    rewrite_target_length: int = 150,
) -> RefreshResult:
    connection = get_connection()
    try:
        known_links = get_known_links(connection)
    finally:
        connection.close()

    articles = fetch_all_sources(
        enrich_articles=enrich_articles,
        max_enriched_articles=max_enriched_articles,
        known_links=known_links,
    )
    connection = get_connection()
    saved = 0
    relevant = 0
    translated = 0
    rewritten = 0
    try:
        for article in articles:
            if article["is_relevant"]:
                relevant += 1
            if upsert_article(connection, article):
                saved += 1

        if auto_translate and has_translation_api_key():
            pending_rows = connection.execute(
                """
                SELECT *
                FROM articles
                WHERE is_relevant = 1
                  AND score >= 18
                  AND (
                    translated_content IS NULL OR translated_content = ''
                    OR rewritten_summary IS NULL OR rewritten_summary = ''
                  )
                ORDER BY COALESCE(published, fetched_at) DESC, score DESC
                """
            ).fetchall()

            for row in pending_rows:
                current_row = row
                if not current_row["translated_content"]:
                    result = translate_article_to_chinese(
                        title=current_row["title"],
                        published=current_row["published"] or "",
                        summary=current_row["summary"] or "",
                        content_text=current_row["content_text"] or current_row["summary"] or current_row["title"],
                    )
                    save_translation(
                        connection,
                        article_id=current_row["id"],
                        translated_title=result.translated_title,
                        translated_summary=result.translated_summary,
                        translated_content=result.translated_content,
                        translated_published=result.translated_published,
                        translated_model=result.model,
                    )
                    translated += 1
                    current_row = connection.execute(
                        "SELECT * FROM articles WHERE id = ?",
                        (current_row["id"],),
                    ).fetchone()

                if current_row and not current_row["rewritten_summary"]:
                    result = rewrite_article_for_engagement(
                        title=current_row["title"],
                        published=current_row["published"] or "",
                        summary=current_row["summary"] or "",
                        content_text=current_row["content_text"] or current_row["summary"] or current_row["title"],
                        translated_title=current_row["translated_title"] or "",
                        translated_summary=current_row["translated_summary"] or "",
                        translated_content=current_row["translated_content"] or "",
                        target_length=rewrite_target_length,
                    )
                    save_rewrite(
                        connection,
                        article_id=current_row["id"],
                        rewritten_title=result.rewritten_title,
                        rewritten_summary=result.rewritten_summary,
                        rewritten_model=result.model,
                    )
                    rewritten += 1
        connection.commit()
    finally:
        connection.close()

    return RefreshResult(
        inserted_or_updated=saved,
        skipped_existing=len(known_links),
        relevant_count=relevant,
        translated_count=translated,
        rewritten_count=rewritten,
        total_count=len(articles),
    )
