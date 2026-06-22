"""
research.py — Firecrawl search + scrape + LLM summarisation.

Flow:
  1. search_topic()  → Firecrawl search for top 3 URLs on the topic
  2. scrape_pages()  → Firecrawl scrape each URL for markdown content
  3. summarize()     → Groq LLM condenses scraped content into a summary

Tenacity retries wrap all Firecrawl API calls.
"""

import os

from firecrawl import FirecrawlApp
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.logger import logger

# Number of search results to scrape
MAX_RESULTS = 3
# Max characters to feed into the summary prompt (avoid token limits)
MAX_CONTENT_CHARS = 6000


def _get_firecrawl() -> FirecrawlApp:
    """Create a Firecrawl client from environment."""
    return FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])


@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def _search(app: FirecrawlApp, query: str) -> list[str]:
    """Search Firecrawl and return a list of URLs."""
    logger.info(f"Firecrawl search: '{query}'")
    results = app.search(query, limit=MAX_RESULTS)
    # results is a SearchData object with a 'web' list
    if hasattr(results, "web") and results.web:
        urls = [r.url for r in results.web if hasattr(r, "url")]
    elif isinstance(results, list):  # fallback for older versions
        urls = [
            r.get("url", "") for r in results if isinstance(r, dict) and r.get("url")
        ]
    else:
        urls = []
    logger.info(f"Found {len(urls)} search result URLs")
    return urls


@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def _scrape(app: FirecrawlApp, url: str) -> str:
    """Scrape a single URL and return its markdown content."""
    logger.info(f"Scraping: {url}")
    result = app.scrape_url(url, formats=["markdown"])
    # result is a ScrapeResponse object; access markdown attribute
    return getattr(result, "markdown", "") or ""


def summarize_research(topic: str, raw_content: str, llm: ChatGroq) -> str:
    """Use Groq LLM to summarise scraped content into research notes."""
    prompt = (
        f"You are a research assistant. Summarise the following web content "
        f"about '{topic}' into concise research notes (max 400 words). "
        f"Focus on key facts, trends, and data points.\n\n"
        f"CONTENT:\n{raw_content[:MAX_CONTENT_CHARS]}"
    )
    logger.info("Summarising research with LLM...")
    response = llm.invoke(prompt)
    return str(response.content)


def search_and_summarize(topic: str, llm: ChatGroq) -> str:
    """
    Main entry point: search topic, scrape pages, summarize.

    Args:
        topic: The chosen blog topic.
        llm:   Groq LLM instance.

    Returns:
        A concise research summary string.
    """
    app = _get_firecrawl()

    # 1. Search for URLs
    try:
        urls = _search(app, topic)
    except Exception as e:
        logger.error(f"Firecrawl search failed: {e}")
        return f"Research unavailable: {e}"

    # 2. Scrape each URL and concatenate content
    all_content = []
    for url in urls:
        try:
            content = _scrape(app, url)
            if content:
                all_content.append(f"--- Source: {url} ---\n{content}")
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")

    if not all_content:
        return "No research content could be retrieved."

    raw = "\n\n".join(all_content)

    # 3. Summarize with LLM
    return summarize_research(topic, raw, llm)
