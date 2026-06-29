# NEW
# Reason: Moved from app/nodes/critic.py and refactored to be asynchronous.
# ------------------------
"""
critic.py — Blog quality review via Groq structured output.

The critic reads the current blog draft and returns:
  - score    : int 0-100
  - feedback : actionable improvement notes

If score >= PASS_SCORE_THRESHOLD (85) or max attempts reached,
the graph routes to save_blog. Otherwise it routes back to write_blog.

Tenacity retries wrap the LLM call.
"""

from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.logger import logger
from app.models.schemas import CriticOutput


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def review_blog(draft: str, llm: ChatGroq) -> CriticOutput:
    """
    Score the blog draft and provide improvement feedback.

    Uses Groq structured output to return a CriticOutput Pydantic model.

    Args:
        draft: The full blog markdown text.
        llm:   Groq LLM instance.

    Returns:
        CriticOutput with score (0-100) and feedback string.
    """
    logger.info("Critic is reviewing the blog draft...")

    prompt = (
        "You are an expert blog editor. Review the following blog article "
        "and score it from 0 to 100 based on:\n"
        "  - Accuracy and depth of content (30 pts)\n"
        "  - Clarity and readability (25 pts)\n"
        "  - Structure and flow (25 pts)\n"
        "  - Engagement and tone (20 pts)\n\n"
        "Provide a score AND specific, actionable feedback to improve it.\n"
        "Be strict — only award 85+ for genuinely high-quality content.\n\n"
        f"BLOG DRAFT:\n{draft}\n\n"
        "Return JSON with 'score' (int) and 'feedback' (str) fields."
    )

    structured_llm = llm.with_structured_output(CriticOutput)
    # CHANGED
    # Reason: Use async ainvoke instead of invoke.
    result: CriticOutput = await structured_llm.ainvoke(prompt)
    # ------------------------
    logger.info(f"Critic score: {result.score}/100")
    return result
# ------------------------
