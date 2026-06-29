"""
database.py — PostgreSQL persistence for the best blog draft using SQLAlchemy.

Two functions:
  - init_db()  : Creates the blog_posts table if it doesn't exist.
  - save_blog(): Inserts the best draft row.

Uses SQLAlchemy 2.0 and asyncpg for async DB operations.
Reads DATABASE_URL from environment and adapts it to postgresql+asyncpg:// if needed.
Tenacity retries wrap all DB operations.
"""

# CHANGED
# Reason: Replaced psycopg2 with SQLAlchemy and asyncpg. Added async support.
# ------------------------
import os
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_fixed
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, Integer, DateTime, func

from app.core.logger import logger

# Retrieve and adapt DATABASE_URL for asyncpg if necessary
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Create SQLAlchemy Async Engine and SessionMaker
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    """Base model class for SQLAlchemy."""
    pass

class BlogPost(Base):
    """SQLAlchemy model representing the blog_posts table."""
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    draft: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def init_db() -> None:
    """
    Create the blog_posts table if it doesn't already exist.
    """
    logger.info("Initialising database table (if not exists) via SQLAlchemy...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready.")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def save_blog(topic: str, draft: str, score: int) -> None:
    """
    Insert the best blog draft into the blog_posts table using SQLAlchemy AsyncSession.

    Args:
        topic: The blog topic.
        draft: The full markdown blog text.
        score: The critic score for this draft.
    """
    logger.info(f"Saving blog to DB (topic='{topic}', score={score}) via SQLAlchemy...")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            new_post = BlogPost(topic=topic, draft=draft, score=score)
            session.add(new_post)
    logger.info("Blog saved successfully.")
# ------------------------
