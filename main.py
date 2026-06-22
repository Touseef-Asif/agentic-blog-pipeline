import uvicorn
from dotenv import load_dotenv

# MUST be first — loads .env before any other module reads os.environ
load_dotenv()


def run():
    """Start the FastAPI server."""
    print("Starting API Server on http://0.0.0.0:8000")
    uvicorn.run("app.api.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
