"""
models.py — Pydantic data models for the blog pipeline.

Three models:
  - Article        : A single RSS article.
  - TopicSelection : LLM-chosen topic with reasoning.
  - CriticOutput   : Score + feedback from the critic node.
"""

from pydantic import BaseModel, Field


class Article(BaseModel):
    """A single article fetched from an RSS feed."""

    title: str
    link: str
    summary: str
    source: str  # e.g. "wsj_tech" or "dawn"


class TopicSelection(BaseModel):
    """Structured output from the topic-selection LLM call."""

    topic: str = Field(description="The single best trending topic to write about.")
    reasoning: str = Field(
        description="One sentence explaining why this topic was chosen."
    )


class CriticOutput(BaseModel):
    """Structured output from the critic LLM call."""

    score: int = Field(ge=0, le=100, description="Quality score 0-100.")
    feedback: str = Field(
        description="Specific, actionable feedback to improve the blog."
    )
