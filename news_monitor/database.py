import json
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent.parent / "data.db"

REQUIRED_COLUMNS = {
    "translated_title": "TEXT",
    "translated_summary": "TEXT",
    "translated_content": "TEXT",
    "translated_model": "TEXT",
    "translated_published": "TEXT",
    "translated_at": "TEXT",
    "rewritten_title": "TEXT",
    "rewritten_summary": "TEXT",
    "rewritten_model": "TEXT",
    "rewritten_at": "TEXT",
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_region TEXT NOT NULL,
    feed_url TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    published TEXT,
    summary TEXT,
    content_text TEXT,
    image_url TEXT,
    score INTEGER NOT NULL DEFAULT 0,
    is_relevant INTEGER NOT NULL DEFAULT 0,
    matched_keywords TEXT NOT NULL DEFAULT '[]',
    chinese_hits TEXT NOT NULL DEFAULT '[]',
    crime_hits TEXT NOT NULL DEFAULT '[]',
    viral_hits TEXT NOT NULL DEFAULT '[]',
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(SCHEMA)
    existing_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(articles)").fetchall()
    }
    for column_name, column_type in REQUIRED_COLUMNS.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE articles ADD COLUMN {column_name} {column_type}"
            )
    return connection


def upsert_article(connection: sqlite3.Connection, article: dict[str, Any]) -> bool:
    cursor = connection.execute(
        """
        INSERT INTO articles (
            source_name, source_region, feed_url, title, link, published, summary,
            content_text, image_url, score, is_relevant, matched_keywords,
            chinese_hits, crime_hits, viral_hits
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(link) DO UPDATE SET
            source_name=excluded.source_name,
            source_region=excluded.source_region,
            feed_url=excluded.feed_url,
            title=excluded.title,
            published=excluded.published,
            summary=excluded.summary,
            content_text=excluded.content_text,
            image_url=excluded.image_url,
            score=excluded.score,
            is_relevant=excluded.is_relevant,
            matched_keywords=excluded.matched_keywords,
            chinese_hits=excluded.chinese_hits,
            crime_hits=excluded.crime_hits,
            viral_hits=excluded.viral_hits,
            fetched_at=CURRENT_TIMESTAMP
        """,
        (
            article["source_name"],
            article["source_region"],
            article["feed_url"],
            article["title"],
            article["link"],
            article.get("published"),
            article.get("summary"),
            article.get("content_text"),
            article.get("image_url"),
            article["score"],
            1 if article["is_relevant"] else 0,
            json.dumps(article["matched_keywords"], ensure_ascii=False),
            json.dumps(article["chinese_hits"], ensure_ascii=False),
            json.dumps(article["crime_hits"], ensure_ascii=False),
            json.dumps(article["viral_hits"], ensure_ascii=False),
        ),
    )
    return cursor.rowcount > 0


def list_articles(
    connection: sqlite3.Connection,
    *,
    relevant_only: bool = True,
    min_score: int = 0,
    source_region: str = "All",
    keyword: str = "",
    limit: int = 200,
) -> list[sqlite3.Row]:
    query = """
    SELECT *
    FROM articles
    WHERE score >= ?
    """
    params: list[Any] = [min_score]

    if relevant_only:
        query += " AND is_relevant = 1"

    if source_region != "All":
        query += " AND source_region = ?"
        params.append(source_region)

    if keyword.strip():
        query += " AND (title LIKE ? OR summary LIKE ? OR content_text LIKE ?)"
        like = f"%{keyword.strip()}%"
        params.extend([like, like, like])

    query += " ORDER BY score DESC, COALESCE(published, fetched_at) DESC LIMIT ?"
    params.append(limit)

    return connection.execute(query, params).fetchall()


def get_regions(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT DISTINCT source_region FROM articles ORDER BY source_region"
    ).fetchall()
    return [row["source_region"] for row in rows]


def get_known_links(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT link FROM articles").fetchall()
    return {row["link"] for row in rows}


def get_monitor_stats(
    connection: sqlite3.Connection,
    *,
    min_score: int,
    relevant_only: bool,
    source_region: str = "All",
) -> dict[str, Any]:
    filters = ["score >= ?"]
    params: list[Any] = [min_score]

    if relevant_only:
        filters.append("is_relevant = 1")

    if source_region != "All":
        filters.append("source_region = ?")
        params.append(source_region)

    where_clause = " AND ".join(filters)
    count_row = connection.execute(
        f"SELECT COUNT(*) AS count FROM articles WHERE {where_clause}",
        params,
    ).fetchone()
    span_row = connection.execute(
        f"""
        SELECT
            MAX(COALESCE(published, fetched_at)) AS newest,
            MIN(COALESCE(published, fetched_at)) AS oldest
        FROM articles
        WHERE {where_clause}
        """,
        params,
    ).fetchone()
    return {
        "count": count_row["count"] if count_row else 0,
        "newest": span_row["newest"] if span_row else None,
        "oldest": span_row["oldest"] if span_row else None,
    }


def save_translation(
    connection: sqlite3.Connection,
    *,
    article_id: int,
    translated_title: str,
    translated_summary: str,
    translated_content: str,
    translated_published: str,
    translated_model: str,
) -> None:
    connection.execute(
        """
        UPDATE articles
        SET translated_title = ?,
            translated_summary = ?,
            translated_content = ?,
            translated_published = ?,
            translated_model = ?,
            translated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            translated_title,
            translated_summary,
            translated_content,
            translated_published,
            translated_model,
            article_id,
        ),
    )


def save_rewrite(
    connection: sqlite3.Connection,
    *,
    article_id: int,
    rewritten_title: str,
    rewritten_summary: str,
    rewritten_model: str,
) -> None:
    connection.execute(
        """
        UPDATE articles
        SET rewritten_title = ?,
            rewritten_summary = ?,
            rewritten_model = ?,
            rewritten_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            rewritten_title,
            rewritten_summary,
            rewritten_model,
            article_id,
        ),
    )
