"""
graph.py — LangGraph StateGraph wiring.

Defines 6 nodes and connects them with normal + conditional edges.

Node execution order:
  fetch_rss → pick_topic → do_research → write_blog → critique_blog
                                                            ↓
                                              [conditional_edge]
                                            /                    \\
                               pass (score≥85 or max attempts)   fail (retry)
                                            ↓                    ↓
                                        save_blog           write_blog (loop)

LangGraph checkpointing uses in-memory MemorySaver (simple, no disk needed).
"""

import os

from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

import app.db.database as database
import app.nodes.critic as critic_module
import app.nodes.research as research_module
import app.nodes.rss as rss
import app.nodes.writer as writer_module
from app.core.logger import logger
from app.core.state import BlogState

# --- Thresholds (read from env, with sane defaults) ---
PASS_SCORE = int(os.getenv("PASS_SCORE_THRESHOLD", "85"))
MAX_ATTEMPTS = int(os.getenv("MAX_CRITIC_ATTEMPTS", "5"))


def _get_llm() -> ChatGroq:
    """Create a Groq LLM instance."""
    return ChatGroq(
        api_key=os.environ["GROQ_API_KEY"],
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.7,
    )


# ─────────────────────────────────────────────
# Node functions — each takes BlogState, returns partial state update
# ─────────────────────────────────────────────


def fetch_rss(state: BlogState) -> dict:
    """Node 1: Fetch articles from OpenAI and Dawn RSS feeds."""
    logger.info("=== NODE: fetch_rss ===")
    articles = rss.fetch_articles()
    return {"articles": articles}


def pick_topic(state: BlogState) -> dict:
    """Node 2: Use LLM to select the single best topic from articles."""
    logger.info("=== NODE: pick_topic ===")
    llm = _get_llm()
    selection = writer_module.select_topic(state["articles"], llm)
    return {"selected_topic": selection.topic}


def do_research(state: BlogState) -> dict:
    """Node 3: Firecrawl search + scrape + LLM summary."""
    logger.info("=== NODE: do_research ===")
    llm = _get_llm()
    summary = research_module.search_and_summarize(state["selected_topic"], llm)
    return {"research_summary": summary}


def write_blog(state: BlogState) -> dict:
    """Node 4: Generate outline then full blog draft (uses critic feedback if retrying)."""
    logger.info("=== NODE: write_blog ===")
    llm = _get_llm()
    topic = state["selected_topic"]
    research = state["research_summary"]
    feedback = state.get("critic_feedback", "")

    # On the first pass, generate the outline; on retries, reuse it
    if not state.get("outline"):
        outline = writer_module.generate_outline(topic, research, llm)
    else:
        outline = state["outline"]

    draft = writer_module.generate_blog(topic, outline, research, feedback, llm)
    return {
        "outline": outline,
        "draft": draft,
        "attempts": state.get("attempts", 0) + 1,
    }


def critique_blog(state: BlogState) -> dict:
    """Node 5: Score the draft and track the best version seen so far."""
    logger.info("=== NODE: critique_blog ===")
    llm = _get_llm()
    result = critic_module.review_blog(state["draft"], llm)

    # Track the best draft across all attempts
    current_best_score = state.get("best_score", 0)
    if result.score > current_best_score:
        best_score = result.score
        best_draft = state["draft"]
        logger.info(f"New best draft! Score: {best_score}")
    else:
        best_score = current_best_score
        best_draft = state.get("best_draft", state["draft"])

    return {
        "critic_score": result.score,
        "critic_feedback": result.feedback,
        "best_score": best_score,
        "best_draft": best_draft,
    }


def save_blog(state: BlogState) -> dict:
    """Node 6: Persist the best draft to PostgreSQL."""
    logger.info("=== NODE: save_blog ===")
    database.save_blog(
        topic=state["selected_topic"],
        draft=state["best_draft"],
        score=state["best_score"],
    )
    logger.info(f"Pipeline complete. Best score: {state['best_score']}/100")
    return {}  # No state changes needed after saving


# ─────────────────────────────────────────────
# Conditional edge — routes after critique_blog
# ─────────────────────────────────────────────


def should_rewrite(state: BlogState) -> str:
    """
    Routing function for the conditional edge after critique_blog.

    Returns:
        "save_blog"  — if score passes threshold OR max attempts reached.
        "write_blog" — if we should retry with critic feedback.
    """
    score = state["critic_score"]
    attempts = state.get("attempts", 0)

    if score >= PASS_SCORE:
        logger.info(f"Score {score} >= {PASS_SCORE}. Sending to save.")
        return "save_blog"
    elif attempts >= MAX_ATTEMPTS:
        logger.warning(f"Max attempts ({MAX_ATTEMPTS}) reached. Saving best draft.")
        return "save_blog"
    else:
        logger.info(
            f"Score {score} < {PASS_SCORE}. Attempt {attempts}/{MAX_ATTEMPTS}. Rewriting..."
        )
        return "write_blog"


# ─────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────


def build_graph():
    """
    Assemble and compile the LangGraph StateGraph.

    Returns a compiled graph ready to invoke.
    """
    graph = StateGraph(BlogState)

    # Register nodes
    graph.add_node("fetch_rss", fetch_rss)
    graph.add_node("pick_topic", pick_topic)
    graph.add_node("do_research", do_research)
    graph.add_node("write_blog", write_blog)
    graph.add_node("critique_blog", critique_blog)
    graph.add_node("save_blog", save_blog)

    # Linear edges (fetch → pick → research → write)
    graph.set_entry_point("fetch_rss")
    graph.add_edge("fetch_rss", "pick_topic")
    graph.add_edge("pick_topic", "do_research")
    graph.add_edge("do_research", "write_blog")
    graph.add_edge("write_blog", "critique_blog")

    # Conditional edge: critique_blog → (save_blog | write_blog)
    graph.add_conditional_edges(
        "critique_blog",
        should_rewrite,
        {
            "save_blog": "save_blog",
            "write_blog": "write_blog",
        },
    )

    # save_blog ends the graph
    graph.add_edge("save_blog", END)

    # Compile with in-memory checkpointing
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
