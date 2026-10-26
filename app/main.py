from app.api import ai_providers, repository, workspace
from app.services.workspace_manager import get_workspace_manager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Forge", version="0.1.0")

# Initialize workspace manager at startup
get_workspace_manager()

app.include_router(repository.router)
app.include_router(workspace.router)
app.include_router(ai_providers.router)

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Forge", "version": "0.1.0"}