"""
rss.py — Fetch latest articles from RSS feeds.

Two hard-coded feeds:
  1. WSJ Tech     — https://feeds.a.dj.com/rss/RSSWSJD.xml
  2. Dawn News    — https://www.dawn.com/feeds/home

Returns a list of Article dicts (5 articles per feed = up to 10 total).
Tenacity retries on network failures.
"""

import feedparser
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.logger import logger
from app.models.schemas import Article

# The two RSS feeds — change URLs here if they ever move
RSS_FEEDS = {
    "wsj_tech": "https://feeds.a.dj.com/rss/RSSWSJD.xml",
    "dawn": "https://www.dawn.com/feeds/home",
}

ARTICLES_PER_FEED = 5  # How many articles to pull from each feed


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _fetch_feed(source: str, url: str) -> list[Article]:
    """Fetch and parse a single RSS feed. Retries up to 3 times."""
    logger.info(f"Fetching RSS feed: {source} ({url})")
    feed = feedparser.parse(url)

    articles = []
    for entry in feed.entries[:ARTICLES_PER_FEED]:
        try:
            article = Article(
                title=entry.get("title", "No title"),
                link=entry.get("link", ""),
                summary=entry.get("summary", ""),
                source=source,
            )
            articles.append(article)
        except Exception as e:
            logger.warning(f"Skipping malformed entry from {source}: {e}")

    logger.info(f"Got {len(articles)} articles from {source}")
    return articles


def fetch_articles() -> list[dict]:
    """
    Fetch articles from all configured RSS feeds.

    Returns:
        List of Article dicts (ready to put into BlogState).
    """
    all_articles = []
    for source, url in RSS_FEEDS.items():
        try:
            articles = _fetch_feed(source, url)
            all_articles.extend(articles)
        except Exception as e:
            logger.error(f"Failed to fetch feed {source} after retries: {e}")

    logger.info(f"Total articles fetched: {len(all_articles)}")
    # Convert Pydantic models to plain dicts for LangGraph state
    return [a.model_dump() for a in all_articles]
