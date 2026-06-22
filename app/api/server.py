import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.db.database import init_db
from app.graph import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the database is initialized before serving requests."""
    init_db()
    yield


app = FastAPI(
    title="Blog Pipeline API",
    description="Streaming API for Blog MVP",
    lifespan=lifespan,
)


@app.post("/chat/stream")
async def chat_stream():
    """
    Stream the execution of the LangGraph blog writing pipeline.
    Yields Server-Sent Events (SSE) indicating progress.
    """
    graph_app = build_graph()

    initial_state = {
        "articles": [],
        "selected_topic": "",
        "research_summary": "",
        "outline": "",
        "draft": "",
        "critic_score": 0,
        "critic_feedback": "",
        "attempts": 0,
        "best_score": 0,
        "best_draft": "",
    }

    config = {"configurable": {"thread_id": "blog-run-streaming"}}

    async def event_generator():
        # Iterate over graph events asynchronously
        async for event in graph_app.astream(initial_state, config=config):
            for node, state_update in event.items():
                message = f"Finished node: {node}"
                if node == "fetch_rss":
                    articles = state_update.get("articles", [])
                    message = f"Fetched {len(articles)} articles from RSS feeds."
                elif node == "pick_topic":
                    message = f"Selected trending topic: '{state_update.get('selected_topic')}'"
                elif node == "do_research":
                    summary = state_update.get("research_summary", "")
                    message = f"Completed deep research (Summary size: {len(summary)} chars)."
                elif node == "write_blog":
                    attempts = state_update.get("attempts", 1)
                    message = f"Drafted blog post (Attempt {attempts})."
                elif node == "critique_blog":
                    score = state_update.get("critic_score", 0)
                    message = f"Critic reviewed draft and gave a score of {score}/100."
                elif node == "save_blog":
                    message = "Persisted best blog draft to database."

                yield f"data: {json.dumps({'node': node, 'message': message})}\n\n"

            # Small yield to the event loop
            await asyncio.sleep(0.1)

        # After completion, retrieve and send the final state
        final_state = graph_app.get_state(config).values
        yield f"data: {json.dumps({'done': True, 'final_state': final_state})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
