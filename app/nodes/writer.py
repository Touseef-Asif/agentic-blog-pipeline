"""
writer.py — Topic selection, outline generation, and blog writing via Groq.

Three functions, each making a single Groq LLM call:
  1. select_topic()      → picks the best topic from articles (structured output)
  2. generate_outline()  → produces a blog outline
  3. generate_blog()     → writes the full blog (incorporating critic feedback)

Tenacity retries wrap all LLM calls.
"""

from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.logger import logger
from app.models.schemas import TopicSelection


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def select_topic(articles: list[dict], llm: ChatGroq) -> TopicSelection:
    """
    Analyse RSS articles and pick the single best topic to write about.

    Uses Groq structured output (with_structured_output) to return a
    TopicSelection Pydantic model.
    """
    logger.info("Selecting best topic from articles...")

    # Build a compact article list for the prompt
    article_lines = "\n".join(
        f"- [{a['source'].upper()}] {a['title']}: {a['summary'][:120]}"
        for a in articles
    )

    prompt = (
        "You are a content strategist. Given these recent news articles, "
        "identify the single most trending and interesting topic to write a blog about. "
        "Choose something that will attract broad readership.\n\n"
        f"ARTICLES:\n{article_lines}\n\n"
        "Return your answer as JSON with 'topic' and 'reasoning' fields."
    )

    # Use structured output — returns a TopicSelection instance directly
    structured_llm = llm.with_structured_output(TopicSelection)
    result: TopicSelection = structured_llm.invoke(prompt)
    logger.info(f"Selected topic: '{result.topic}' — {result.reasoning}")
    return result


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_outline(topic: str, research_summary: str, llm: ChatGroq) -> str:
    """Generate a structured blog outline for the given topic."""
    logger.info(f"Generating outline for: '{topic}'")
    prompt = (
        f"Create a detailed blog outline for the topic: '{topic}'\n\n"
        f"Use this research as a foundation:\n{research_summary}\n\n"
        "Return a markdown outline with an introduction, 3-4 main sections "
        "(each with 2-3 bullet sub-points), and a conclusion."
    )
    response = llm.invoke(prompt)
    return str(response.content)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def generate_blog(
    topic: str,
    outline: str,
    research_summary: str,
    feedback: str,
    llm: ChatGroq,
) -> str:
    """
    Write a complete blog article.

    If `feedback` is non-empty, it means we're rewriting based on critic notes.
    """
    logger.info(f"Writing blog draft for: '{topic}' (feedback: {bool(feedback)})")

    feedback_section = (
        f"\n\nCRITIC FEEDBACK TO ADDRESS:\n{feedback}" if feedback else ""
    )

    prompt = (
        f"Write a complete, engaging blog article about: '{topic}'\n\n"
        f"OUTLINE TO FOLLOW:\n{outline}\n\n"
        f"RESEARCH NOTES:\n{research_summary}"
        f"{feedback_section}\n\n"
        "Requirements:\n"
        "- 600-900 words\n"
        "- Markdown format with headers\n"
        "- Engaging introduction and strong conclusion\n"
        "- Use facts from the research\n"
        "- Professional but accessible tone"
    )
    response = llm.invoke(prompt)
    return str(response.content)
