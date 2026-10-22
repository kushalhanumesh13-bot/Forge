from pathlib import Path
import os
import shutil
import subprocess
import sys

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.analyzer import RepositoryAnalyzer
from app.services.engineering_brain import EngineeringBrain
from app.services.engineering_tools import SearchFilesRequest, SearchFilesTool
from app.services.conclusion import WorkflowConclusionBuilder
from app.services.repository import RepositoryService


router = APIRouter(prefix="/api", tags=["workspace"])
ROOT = Path.cwd().resolve()
LOCAL_GIT = ROOT / "Git" / "cmd" / "git.exe"

_active_plan: dict | None = None
_active_verification: dict | None = None


def _reset_workflow_state() -> None:
    global _active_plan, _active_verification
    _active_plan = None
    _active_verification = None


def _set_active_verification(data: dict) -> None:
    global _active_verification
    _active_verification = data


class RepositoryRequest(BaseModel):
    path: str | None = None


class FileWriteRequest(BaseModel):
    path: str
    content: str


class TaskRequest(BaseModel):
    repo: str | None = None
    description: str = Field(min_length=1, max_length=4000)
    targets: list[str] | None = None
    scope: list[str] | None = None
    constraints: list[str] | None = None


class ConclusionRequest(BaseModel):
    taskId: str | None = None
    verification: dict | None = None


class CommandRequest(BaseModel):
    repo: str | None = None
    command: str = Field(min_length=1, max_length=200)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=512)


# Windows reserved device names (case-insensitive)
_WIN_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _is_windows_reserved(name: str) -> bool:
    """Check if a path component is a Windows reserved device name."""
    # Handle names with extensions (e.g., CON.txt, CON.)
    base = name.split(".", 1)[0].upper()
    return base in _WIN_RESERVED_NAMES


def _workspace_path(relative_path: str) -> Path:
    """Resolve a workspace-relative path without allowing traversal or symlinks."""
    if not isinstance(relative_path, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid workspace path",
        )

    # Reject empty or whitespace-only paths
    if not relative_path or not relative_path.strip():
        raise HTTPException(
            status_code=400,
            detail="Path must be a non-empty string",
        )

    # Reject paths with trailing slashes (indicate directory, not file)
    if relative_path.endswith("/") or relative_path.endswith("\\"):
        raise HTTPException(
            status_code=400,
            detail="Path must not end with a directory separator",
        )

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

    # Reject Windows reserved names in any path component
    for part in supplied.parts:
        if part not in ("", ".") and _is_windows_reserved(part):
            raise HTTPException(
                status_code=400,
                detail="Path component uses a reserved device name",
            )

    # Reject trailing dots, spaces, or control characters in the final component
    final_part = supplied.parts[-1] if supplied.parts else ""
    if final_part.endswith(".") or final_part.rstrip() != final_part:
        raise HTTPException(
            status_code=400,
            detail="Path must not end with a dot, space, or control character",
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
    global _active_plan
    task_input = {
        "description": request.description,
        "targets": request.targets or [],
        "scope": request.scope or [],
        "constraints": request.constraints or [],
    }
    plan = EngineeringBrain(_analysis()).generate_plan(task_input)
    task = plan["task"]

    _active_plan = {
        "taskId": "local-plan",
        "status": "complete",
        "classification": task["type"],
        "confidence": plan["confidence"],
        "plan": plan,
    }
    return _active_plan


@router.get("/task/plan")
def get_task_plan(id: str = "local-plan"):
    if id != "local-plan":
        raise HTTPException(status_code=404, detail="Plan not found")

    if _active_plan is None:
        return {
            "taskId": id,
            "status": "empty",
            "steps": [],
        }

    return {
        "taskId": id,
        "status": _active_plan["status"],
        "classification": _active_plan.get("classification"),
        "confidence": _active_plan.get("confidence"),
        "steps": _active_plan.get("plan", {}).get("steps", []),
        "plan": _active_plan.get("plan", {}),
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

    if os.environ.get("FORGE_TEST_COMMAND_ACTIVE") == "1":
        res = {
            "commandId": "local-command",
            "command": command,
            "output": "Skipped recursive Forge test-command invocation.\n",
            "exitCode": 0,
        }
        _set_active_verification(res)
        return res

    try:
        environment = os.environ.copy()
        environment["FORGE_TEST_COMMAND_ACTIVE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=environment,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        res = {
            "commandId": "local-command",
            "command": command,
            "output": (
                stdout
                + stderr
                + "\nTest command timed out after 300 seconds."
            ),
            "exitCode": 124,
        }
        _set_active_verification(res)
        return res
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start the test command",
        ) from error

    res = {
        "commandId": "local-command",
        "command": command,
        "output": completed.stdout + completed.stderr,
        "exitCode": completed.returncode,
    }
    _set_active_verification(res)
    return res


def _build_conclusion(request: ConclusionRequest | None = None) -> dict:
    changes_resp = list_changes()
    changes = changes_resp.get("changes", [])

    diffs: dict[str, str] = {}
    for change in changes:
        path = change.get("path")
        if path:
            try:
                diff_res = get_change_diff(path)
                diffs[path] = diff_res.get("diff", "")
            except Exception:
                diffs[path] = ""

    verification = None
    if request and request.verification:
        verification = request.verification
    elif _active_verification:
        verification = _active_verification

    builder = WorkflowConclusionBuilder(
        plan=_active_plan,
        changes=changes,
        diffs=diffs,
        verification=verification,
    )
    return builder.build()


@router.get("/conclusion")
def get_conclusion():
    return _build_conclusion(None)


@router.post("/conclusion")
def create_conclusion(request: ConclusionRequest | None = None):
    return _build_conclusion(request)