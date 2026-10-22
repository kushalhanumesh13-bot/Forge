"""End-to-end integration test verifying the complete Forge engineering workflow.

Pipeline:
UNDERSTAND -> INVESTIGATE -> PLAN -> INSPECT -> MODIFY -> REVIEW -> VERIFY -> CONCLUDE
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.workspace import _reset_workflow_state


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_workflow_state():
    """Ensure in-memory workflow state is clean for each test."""
    _reset_workflow_state()
    yield
    _reset_workflow_state()


def test_complete_engineering_workflow_e2e():
    """Verify the full 8-stage engineering lifecycle through the FastAPI interface."""
    # Prevent recursive pytest execution during test run
    os.environ["FORGE_TEST_COMMAND_ACTIVE"] = "1"

    # --- STAGE 0: Health & Service Availability ---
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # --- STAGE 1: UNDERSTAND ---
    # Trigger repository analysis to map code structure and symbols
    analyze_resp = client.post("/api/repository/analyze", json={})
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()
    assert "codebase_understanding" in analysis
    assert "summary" in analysis
    assert len(analysis["codebase_understanding"].get("files", [])) > 0

    # --- STAGE 2: INVESTIGATE ---
    # Search for an engineering symbol in the repository
    search_resp = client.post("/api/search", json={"query": "RepositoryAnalyzer"})
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["match_count"] > 0
    investigated_files = [m["path"] for m in search_data["matches"]]
    assert any("analyzer.py" in p for p in investigated_files)

    # --- STAGE 3: PLAN ---
    # Submit an engineering task informed by the investigation findings
    task_desc = "Optimize repository analyzer symbol parsing performance"
    plan_resp = client.post("/api/task/submit", json={
        "description": task_desc,
        "targets": ["app/services/analyzer.py"],
        "scope": ["app/services/analyzer.py", "tests/test_analyzer.py"],
    })
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["taskId"] == "local-plan"
    assert plan_data["status"] == "complete"
    assert "plan" in plan_data
    steps = plan_data["plan"].get("steps", [])
    assert len(steps) > 0

    # Verify plan retrieval endpoint preserves context
    get_plan_resp = client.get("/api/task/plan?id=local-plan")
    assert get_plan_resp.status_code == 200
    retrieved_plan = get_plan_resp.json()
    assert retrieved_plan["status"] == "complete"
    assert len(retrieved_plan["steps"]) == len(steps)

    # --- STAGE 4: INSPECT ---
    # Read the target file to inspect the existing implementation
    file_resp = client.get("/api/file?path=app/services/analyzer.py")
    assert file_resp.status_code == 200
    file_data = file_resp.json()
    assert file_data["path"] == "app/services/analyzer.py"
    assert "class RepositoryAnalyzer" in file_data["content"]
    assert "lastModified" in file_data

    # --- STAGE 5: MODIFY ---
    # Safely modify a testable file with controlled writes
    # Read README.md, append a benign verification comment, then restore it
    readme_resp = client.get("/api/file?path=README.md")
    assert readme_resp.status_code == 200
    original_readme = readme_resp.json()["content"]

    try:
        modified_content = original_readme + "\n<!-- workflow-verification-marker -->\n"
        write_resp = client.post("/api/file/write", json={
            "path": "README.md",
            "content": modified_content,
        })
        assert write_resp.status_code == 200
        assert write_resp.json()["success"] is True

        # --- STAGE 6: REVIEW ---
        # Query Git status and review diffs
        changes_resp = client.get("/api/changes")
        assert changes_resp.status_code == 200
        changes = changes_resp.json()["changes"]
        changed_paths = [c["path"] for c in changes]
        assert any("README.md" in p for p in changed_paths)

        diff_resp = client.get("/api/changes/diff?path=README.md")
        assert diff_resp.status_code == 200
        diff_data = diff_resp.json()
        assert "workflow-verification-marker" in diff_data["diff"]

        # Prior to verification, conclusion reports UNVERIFIED_CHANGES
        pre_verify_conclusion = client.get("/api/conclusion").json()
        assert pre_verify_conclusion["verdict"] == "UNVERIFIED_CHANGES"
        assert pre_verify_conclusion["is_verified"] is False
        assert pre_verify_conclusion["changes"]["total_files"] >= 1

        # --- STAGE 7: VERIFY ---
        # Execute the repository verification command
        command_resp = client.post("/api/command/run", json={"command": "pytest -q"})
        assert command_resp.status_code == 200
        cmd_result = command_resp.json()
        assert "commandId" in cmd_result
        assert "output" in cmd_result
        assert cmd_result["exitCode"] == 0

        # --- STAGE 8: CONCLUDE ---
        # Query the synthesized evidence-backed conclusion
        conclusion_resp = client.get("/api/conclusion")
        assert conclusion_resp.status_code == 200
        conclusion = conclusion_resp.json()

        assert conclusion["verdict"] == "VERIFIED_SUCCESS"
        assert conclusion["is_verified"] is True
        assert conclusion["task"]["objective"] != ""
        assert conclusion["changes"]["total_files"] >= 1
        assert conclusion["verification"]["has_run"] is True
        assert conclusion["verification"]["success"] is True
        assert conclusion["stages"]["conclude"]["status"] == "completed"
        assert "passed" in conclusion["summary"].lower()

    finally:
        # Restore the original file content
        client.post("/api/file/write", json={
            "path": "README.md",
            "content": original_readme,
        })


def test_conclusion_reflects_verification_failure_honestly():
    """Verify that a failing test run produces an honest failure verdict."""
    client.post("/api/task/submit", json={"description": "Fix broken edge case"})

    # Post an overridden verification with a non-zero exit code
    resp = client.post("/api/conclusion", json={
        "verification": {
            "command": "pytest -q",
            "exitCode": 1,
            "output": "1 failed, 5 passed in 0.4s",
        }
    })
    assert resp.status_code == 200
    conclusion = resp.json()

    assert conclusion["verdict"] == "VERIFICATION_FAILED"
    assert conclusion["is_verified"] is False
    assert conclusion["verification"]["failed"] == 1
    assert conclusion["verification"]["success"] is False
    assert "failed" in conclusion["summary"].lower()


def test_command_security_boundaries_preserved():
    """Verify that unallowed commands cannot be executed through the API."""
    resp = client.post("/api/command/run", json={"command": "cat /etc/passwd"})
    assert resp.status_code == 400
    assert "test command" in resp.json()["detail"].lower()
