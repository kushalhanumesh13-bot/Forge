from pathlib import Path
import shutil
import subprocess
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.analyzer import RepositoryAnalyzer
from app.services.engineering_brain import EngineeringBrain
from app.services.engineering_tools import SearchFilesRequest, SearchFilesTool
from app.services.repository import RepositoryService


router = APIRouter(prefix="/api", tags=["workspace"])
ROOT = Path.cwd().resolve()
LOCAL_GIT = ROOT / "Git" / "cmd" / "git.exe"


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
    """Resolve a workspace-relative path without allowing traversal or symlinks."""
    try:
        supplied = Path(relative_path)
    except (TypeError, ValueError, OSError, RuntimeError) as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid workspace path",
        ) from error

    if supplied.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="Path must be relative to the workspace",
        )

    if ".." in supplied.parts:
        raise HTTPException(
            status_code=400,
            detail="Path must stay inside the workspace",
        )

    candidate = ROOT / supplied
    current = ROOT

    for part in supplied.parts:
        if part in ("", "."):
            continue

        current /= part
        if current.is_symlink():
            raise HTTPException(
                status_code=400,
                detail="Symlink paths are not allowed",
            )

    try:
        candidate = candidate.resolve()
    except (OSError, RuntimeError) as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid workspace path",
        ) from error

    if candidate != ROOT and ROOT not in candidate.parents:
        raise HTTPException(
            status_code=400,
            detail="Path must stay inside the workspace",
        )

    return candidate


def _git_executable() -> str:
    if LOCAL_GIT.is_file():
        return str(LOCAL_GIT)
    executable = shutil.which("git")
    if executable:
        return executable
    raise HTTPException(status_code=503, detail="Git executable was not found")


def _analysis() -> dict:
    return RepositoryAnalyzer(RepositoryService(ROOT)).analyze()


@router.post("/repository/analyze")
def analyze_workspace(request: RepositoryRequest):
    if request.path:
        try:
            requested_root = Path(request.path).resolve()
        except (TypeError, ValueError, OSError, RuntimeError) as error:
            raise HTTPException(
                status_code=400,
                detail="Invalid repository path",
            ) from error

        if requested_root != ROOT:
            raise HTTPException(
                status_code=400,
                detail="This workspace is fixed to the running Forge project",
            )

    return _analysis()


@router.get("/file")
def read_file(path: str):
    file_path = _workspace_path(path)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8")
        modified = file_path.stat().st_mtime
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=415,
            detail="File is not UTF-8 text",
        ) from error
    except OSError as error:
        raise HTTPException(
            status_code=400,
            detail="Unable to read file",
        ) from error

    return {
        "path": path,
        "content": content,
        "lastModified": modified,
    }


@router.post("/file/write")
def write_file(request: FileWriteRequest):
    file_path = _workspace_path(request.path)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path.write_text(request.content, encoding="utf-8")
    except OSError as error:
        raise HTTPException(
            status_code=400,
            detail="Unable to write file",
        ) from error

    return {
        "success": True,
        "path": request.path,
    }


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

    return {
        "taskId": id,
        "steps": [],
    }


@router.post("/search")
def search_workspace(request: SearchRequest):
    result = SearchFilesTool().execute(
        SearchFilesRequest(
            repository_root=ROOT,
            query=request.query,
        )
    )

    if not result.success:
        message = (
            result.error.message
            if result.error
            else "Search failed"
        )
        raise HTTPException(status_code=400, detail=message)

    return result.data


@router.get("/changes")
def list_changes():
    git = _git_executable()
    try:
        completed = subprocess.run(
            [git, "-C", str(ROOT), "status", "--short"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            status_code=504,
            detail="Git status timed out",
        ) from error

    if completed.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="Unable to read Git status",
        )

    changes = []

    for line in completed.stdout.splitlines():
        if len(line) >= 4:
            changes.append(
                {
                    "status": line[:2].strip() or "?",
                    "path": line[3:],
                }
            )

    return {"changes": changes}


@router.get("/changes/diff")
def get_change_diff(path: str):
    _workspace_path(path)
    git = _git_executable()

    try:
        completed = subprocess.run(
            [
                git,
                "-C",
                str(ROOT),
                "diff",
                "--no-ext-diff",
                "--",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise HTTPException(
            status_code=504,
            detail="Git diff timed out",
        ) from error

    if completed.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail="Unable to read file diff",
        )

    return {
        "path": path,
        "diff": completed.stdout,
        "status": completed.returncode,
    }


@router.post("/command/run")
def run_command(request: CommandRequest):
    command = request.command.strip()

    allowed_commands = {
        "python -m pytest -q",
        "pytest -q",
    }

    if command not in allowed_commands:
        raise HTTPException(
            status_code=400,
            detail="Only the repository test command is enabled",
        )

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return {
            "commandId": "local-command",
            "output": (
                stdout
                + stderr
                + "\nTest command timed out after 120 seconds."
            ),
            "exitCode": 124,
        }
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start the test command",
        ) from error

    return {
        "commandId": "local-command",
        "output": completed.stdout + completed.stderr,
        "exitCode": completed.returncode,
    }