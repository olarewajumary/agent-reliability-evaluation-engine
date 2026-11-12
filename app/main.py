from fastapi import FastAPI

from app.api.routes import router as evaluation_router


app = FastAPI(
    title="Agent Reliability & Evaluation Engine",
    description=(
        "A system for testing, evaluating, and monitoring "
        "the reliability of tool-using AI agents."
    ),
    version="0.1.0",
)

app.include_router(evaluation_router)


@app.get("/")
async def root():
    """Return basic information about the application."""

    return {
        "name": "Agent Reliability & Evaluation Engine",
        "status": "running",
        "version": "0.1.0",
        "message": "Welcome to the Agent Reliability & Evaluation Engine.",
    }


@app.get("/health")
async def health_check():
    """Check whether the application is healthy."""

    return {"status": "healthy"}