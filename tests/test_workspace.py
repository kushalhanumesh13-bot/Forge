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