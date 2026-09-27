from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.repository import router as repository_router
from app.api.workspace import router as workspace_router

app = FastAPI(
    title="Forge",
    description="An AI powered engineering workspace.",
    version="0.1.0",
)

app.include_router(repository_router)
app.include_router(workspace_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def forge_workspace():
    return FileResponse("app/static/index.html")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Forge",
        "version": "0.1.0"
        
    }