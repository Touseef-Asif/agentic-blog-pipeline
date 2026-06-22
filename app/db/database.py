"""
database.py — PostgreSQL persistence for the best blog draft.

Two functions:
  - init_db()  : Creates the blog_posts table if it doesn't exist.
  - save_blog(): Inserts the best draft row.

Uses plain psycopg2 (no ORM, no migrations).
Reads DATABASE_URL from environment.
Tenacity retries wrap all DB operations.
"""

import os
from datetime import datetime, timezone

import psycopg2
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.logger import logger


def _get_conn():
    """Open a new psycopg2 connection from DATABASE_URL."""
    url = os.environ["DATABASE_URL"]
    return psycopg2.connect(url)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def init_db() -> None:
    """
    Create the blog_posts table if it doesn't already exist.

    Columns:
      id         — auto-increment primary key
      topic      — the blog topic string
      draft      — full markdown blog text
      score      — critic score (0-100)
      created_at — UTC timestamp
    """
    logger.info("Initialising database table (if not exists)...")
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS blog_posts (
                        id         SERIAL PRIMARY KEY,
                        topic      TEXT        NOT NULL,
                        draft      TEXT        NOT NULL,
                        score      INTEGER     NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """)
        logger.info("Database ready.")
    finally:
        conn.close()


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def save_blog(topic: str, draft: str, score: int) -> None:
    """
    Insert the best blog draft into the blog_posts table.

    Args:
        topic: The blog topic.
        draft: The full markdown blog text.
        score: The critic score for this draft.
    """
    logger.info(f"Saving blog to DB (topic='{topic}', score={score})...")
    conn = _get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO blog_posts (topic, draft, score, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (topic, draft, score, datetime.now(timezone.utc)),
                )
        logger.info("Blog saved successfully.")
    finally:
        conn.close()
