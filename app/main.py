from fastapi import FastAPI

app = FastAPI(
    title="Forge",
    description="An AI powered engineering workspace.",
    version="0.1.0",
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Forge",
        }
