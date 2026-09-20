from fastapi import FastAPI

from app.api.repository import router as repository_router

app = FastAPI(
    title="Forge",
    description="An AI powered engineering workspace.",
    version="0.1.0",
)

app.include_router(repository_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Forge",
        "version": "0.1.0"
        
    }