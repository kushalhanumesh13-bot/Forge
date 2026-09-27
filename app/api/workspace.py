from pathlib import Path
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.analyzer import RepositoryAnalyzer
from app.services.engineering_brain import EngineeringBrain
from app.services.engineering_tools import SearchFilesRequest, SearchFilesTool
from app.services.repository import RepositoryService


router = APIRouter(prefix="/api", tags=["workspace"])
ROOT = Path.cwd().resolve()


class RepositoryRequest(BaseModel):
    path: str | None = None


class FileWriteRequest(BaseModel):
    path: str
    content: str


class TaskRequest(BaseModel):
    repo: str | None = None
    description: str = Field(min_length=1, max_length=4000)


class CommandRequest(BaseModel):
    repo: str | None = None
    command: str = Field(min_length=1, max_length=200)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=512)


def _workspace_path(relative_path: str) -> Path:
    candidate = (ROOT / relative_path).resolve()
    if candidate != ROOT and ROOT not in candidate.parents:
        raise HTTPException(status_code=400, detail="Path must stay inside the workspace")
    return candidate


def _analysis() -> dict:
    return RepositoryAnalyzer(RepositoryService(ROOT)).analyze()


@router.post("/repository/analyze")
def analyze_workspace(request: RepositoryRequest):
    if request.path and Path(request.path).resolve() != ROOT:
        raise HTTPException(status_code=400, detail="This workspace is fixed to the running Forge project")
    return _analysis()


@router.get("/file")
def read_file(path: str):
    file_path = _workspace_path(path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        return {"path": path, "content": file_path.read_text(encoding="utf-8"), "lastModified": file_path.stat().st_mtime}
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=415, detail="File is not UTF-8 text") from error


@router.post("/file/write")
def write_file(request: FileWriteRequest):
    file_path = _workspace_path(request.path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    file_path.write_text(request.content, encoding="utf-8")
    return {"success": True, "path": request.path}


@router.post("/task/submit")
def submit_task(request: TaskRequest):
    plan = EngineeringBrain(_analysis()).generate_plan(request.description)
    task = plan["task"]
    return {
        "taskId": "local-plan",
        "status": "complete",
        "classification": task["type"],
        "confidence": plan["confidence"],
        "plan": plan,
    }


@router.get("/task/plan")
def get_task_plan(id: str):
    if id != "local-plan":
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"taskId": id, "steps": []}


@router.post("/search")
def search_workspace(request: SearchRequest):
    result = SearchFilesTool().execute(
        SearchFilesRequest(repository_root=ROOT, query=request.query)
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error.message if result.error else "Search failed")
    return result.data


@router.get("/changes")
def list_changes():
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    changes = []
    for line in completed.stdout.splitlines():
        if len(line) >= 4:
            changes.append({"status": line[:2].strip() or "?", "path": line[3:]})
    return {"changes": changes}


@router.get("/changes/diff")
def get_change_diff(path: str):
    _workspace_path(path)
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--no-ext-diff", "--", path],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return {"path": path, "diff": completed.stdout, "status": completed.returncode}


@router.post("/command/run")
def run_command(request: CommandRequest):
    command = request.command.strip()
    if command not in {"python -m pytest -q", "pytest -q"}:
        raise HTTPException(status_code=400, detail="Only the repository test command is enabled")
    completed = subprocess.run(
        ["python", "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return {
        "commandId": "local-command",
        "output": completed.stdout + completed.stderr,
        "exitCode": completed.returncode,
    }