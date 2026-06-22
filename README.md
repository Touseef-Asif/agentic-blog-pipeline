# 🤖 Blog Pipeline

> A **production-ready agentic blog-writing pipeline** powered by [LangGraph](https://github.com/langchain-ai/langgraph), [Groq](https://groq.com/), and [Firecrawl](https://www.firecrawl.dev/).

Automatically discovers trending topics from RSS feeds, researches them using web scraping, writes high-quality long-form blog posts via LLM, iteratively improves them through a critic-writer loop, and persists the final output to PostgreSQL.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 📰 **RSS Ingestion** | Concurrent multi-feed parsing with deduplication |
| 🔍 **Trend Detection** | LLM-powered topic identification with relevance scoring |
| 🔬 **Deep Research** | Multi-query Firecrawl search + scrape with de-dup |
| ✍️ **AI Writing** | Groq (Llama 3.3 70B) generates 1500–2500 word posts |
| 🔄 **Quality Loop** | Critic evaluates 5 dimensions; writer revises until score ≥ 85 |
| 💾 **PostgreSQL** | Full run history with metrics, drafts, and scores |
| 🖥️ **Rich CLI** | Typer + Rich with progress bars, tables, and panels |
| 📄 **Export** | Markdown and HTML export of published posts |
| 🔁 **Checkpointing** | LangGraph PostgreSQL checkpointer (MemorySaver fallback) |

---

## 🏗️ Architecture

```
RSS Feeds
    │
    ▼
┌─────────────┐
│  fetch_rss  │  Fetch articles from configured RSS feeds
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ pick_topic  │  LLM selects the best topic from articles
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ do_research │  Firecrawl search + scrape + LLM summary
└──────┬──────┘
       │
       ▼
┌──────────────┐◄───────────────────────────┐
│  write_blog  │  Generate outline & draft  │
└──────┬───────┘                            │
       │                                    │ (score < 85 AND attempts < max)
       ▼                                    │
┌───────────────┐                           │
│ critique_blog │─── should_rewrite() ──────┘
└──────┬────────┘
       │ (score ≥ 85 OR attempts ≥ max)
       ▼
┌─────────────┐
│  save_blog  │  Save best Blog draft → PostgreSQL
└──────┬──────┘
       │
      END
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Docker & Docker Compose (for PostgreSQL)
- Groq API key
- Firecrawl API key

### 2. Clone & Install

```bash
git clone https://github.com/your-org/blog-pipeline.git
cd blog-pipeline

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# Install with dev dependencies
pip install -e ".[dev]"
```

### 3. Configure Environment

```bash
# The .env file is pre-configured with working keys:
cat .env
```

Or copy the template and fill in your own keys:

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Start PostgreSQL

Ensure you have a PostgreSQL database running and update the `DATABASE_URL` in `.env`.
*The application will automatically initialize the database schema on startup.*

### 5. Run the Pipeline Server

```bash
python main.py
```
This will start the FastAPI server on `http://localhost:8000`.

### 6. Trigger the Pipeline

In a separate terminal, run the streaming CLI client to monitor progress:

```bash
python scripts/cli.py
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model ID |
| `FIRECRAWL_API_KEY` | — | Firecrawl API key |
| `DATABASE_URL` | `postgresql+psycopg://...` | SQLAlchemy connection string |
| `MAX_CRITIC_ATTEMPTS` | `5` | Max writer-critic loop iterations |
| `PASS_SCORE_THRESHOLD` | `85` | Minimum critic score to accept |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_DIR` | `logs` | Log file directory |

---

## 📁 Project Structure

```
blog-pipeline/
├── .env                    # Environment variables (pre-configured)
├── .env.example            # Template for custom configuration
├── requirements.txt        # Project dependencies
├── init-db.sh              # DB initialization script for PostgreSQL
├── main.py                 # FastAPI server entry point
│
├── app/
│   ├── api/
│   │   └── server.py       # Streaming API endpoints
│   ├── core/
│   │   ├── logger.py       # Logging configuration
│   │   └── state.py        # LangGraph State definition
│   ├── db/
│   │   └── database.py     # Database init and save functions
│   ├── models/
│   │   └── schemas.py      # Pydantic data models
│   ├── nodes/              # Pipeline processing nodes
│   │   ├── rss.py
│   │   ├── research.py
│   │   ├── writer.py
│   │   └── critic.py
│   └── graph.py            # LangGraph StateGraph wiring
│
└── scripts/
    └── cli.py              # CLI client to consume the streaming API
```

---

## 🧪 Development

```bash
# Run tests
make test
# or: pytest tests/ -v

# Lint
make lint

# Format code
make format

# Docker helpers
make docker-up
make docker-down

# Full clean
make clean
```

---

## 📊 Quality Loop

The critic-writer loop works as follows:

```python
def should_rewrite(state: BlogState) -> str:
    score = state["critic_score"]
    attempts = state.get("attempts", 0)

    if score >= PASS_SCORE:
        return "save_blog"    # ✅ ACCEPT
    elif attempts >= MAX_ATTEMPTS:
        return "save_blog"    # ⏹ ACCEPT_BEST (best effort)
    else:
        return "write_blog"   # 🔄 CONTINUE (revise)
```

The critic evaluates 5 dimensions:
- **Clarity** (20%) — Readability and logical flow
- **Depth** (25%) — Substance and insight quality
- **Structure** (20%) — Organisation and headings
- **Engagement** (20%) — Hook, tone, and CTA
- **Accuracy** (15%) — Factual correctness

---

## 🐳 Docker

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f postgres

# Stop
docker-compose down

# Remove volumes (reset DB)
docker-compose down -v
```

---

## 📝 License

MIT © Blog Pipeline Team
