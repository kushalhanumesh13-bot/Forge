from pathlib import Path

import pytest

from fastapi import HTTPException

import app.api.workspace as workspace_api
from app.api.workspace import (
    CommandRequest,
    SearchRequest,
    _workspace_path,
    list_changes,
    run_command,
    search_workspace,
)


def test_workspace_path_stays_inside_repository():
    assert _workspace_path("app/main.py").name == "main.py"


def test_workspace_path_rejects_traversal():
    with pytest.raises(Exception, match="inside the workspace"):
        _workspace_path("../outside.txt")


@pytest.mark.parametrize("path", [
    r"C:\outside.txt",
    r"C:/outside.txt",
    r"..\outside.txt",
    "../outside.txt",
])
def test_workspace_path_rejects_windows_absolute_and_traversal_paths(path):
    with pytest.raises(HTTPException) as error:
        _workspace_path(path)

    assert error.value.status_code == 400


def test_workspace_path_rejects_symlink_components(tmp_path, monkeypatch):
    target = tmp_path / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    link = tmp_path / "linked.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are unavailable in this environment")

    monkeypatch.setattr(workspace_api, "ROOT", tmp_path)
    with pytest.raises(HTTPException, match="Symlink"):
        workspace_api._workspace_path("linked.txt")


def test_search_workspace_returns_real_repository_matches():
    result = search_workspace(SearchRequest(query="RepositoryAnalyzer"))

    assert result["match_count"] > 0
    assert any(match["path"].endswith("analyzer.py") for match in result["matches"])


def test_list_changes_returns_structured_git_status():
    result = list_changes()

    assert isinstance(result["changes"], list)
    assert all({"status", "path"} <= set(change) for change in result["changes"])


def test_run_command_rejects_unapproved_commands():
    with pytest.raises(HTTPException, match="test command"):
        run_command(CommandRequest(command="python -c print(1)"))

def test_task_submit_and_get_plan():
    from app.api.workspace import TaskRequest, submit_task, get_task_plan, _reset_workflow_state
    _reset_workflow_state()

    # Before submitting, plan is empty
    empty_plan = get_task_plan("local-plan")
    assert empty_plan["status"] == "empty"
    assert empty_plan["steps"] == []

    # Submit task with targets
    result = submit_task(TaskRequest(
        description="Fix bug in repository analyzer",
        targets=["app/services/analyzer.py"]
    ))
    assert result["taskId"] == "local-plan"
    assert result["status"] == "complete"
    assert len(result["plan"]["steps"]) > 0

    # Get active plan returns actual generated steps
    plan = get_task_plan("local-plan")
    assert plan["taskId"] == "local-plan"
    assert plan["status"] == "complete"
    assert len(plan["steps"]) > 0
    assert any("analyzer.py" in str(step.get("targets", [])) for step in plan["steps"])


def test_conclusion_generation_and_verdict():
    from app.api.workspace import (
        TaskRequest,
        submit_task,
        get_conclusion,
        create_conclusion,
        ConclusionRequest,
        _reset_workflow_state,
        _set_active_verification,
    )
    _reset_workflow_state()

    # Initial conclusion without verification or plan
    c0 = get_conclusion()
    assert "verdict" in c0
    assert "status" in c0
    assert "stages" in c0
    assert c0["stages"]["conclude"]["status"] == "completed"

    # Set active plan
    submit_task(TaskRequest(description="Investigate workspace search", targets=["app/api/workspace.py"]))

    # Simulate passing verification
    _set_active_verification({
        "commandId": "local-command",
        "command": "pytest -q",
        "output": "10 passed in 0.5s",
        "exitCode": 0,
    })

    c1 = get_conclusion()
    assert c1["task"]["objective"] != ""
    assert c1["verification"]["passed"] == 10
    assert c1["verification"]["success"] is True

    # Test override with failing verification
    c2 = create_conclusion(ConclusionRequest(
        verification={"command": "pytest -q", "exitCode": 1, "output": "1 failed, 9 passed in 0.5s"}
    ))
    assert c2["verification"]["failed"] == 1
    assert c2["verification"]["success"] is False
    assert c2["verdict"] == "VERIFICATION_FAILED"
    assert "failed" in c2["summary"].lower()
