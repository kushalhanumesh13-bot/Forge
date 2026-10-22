"""Unit tests for the workflow conclusion builder and metric parser."""

from app.services.conclusion import WorkflowConclusionBuilder, parse_test_output


def test_parse_test_output_clean_success():
    output = "collected 15 items\n\n15 passed in 1.25s\n"
    res = parse_test_output(output, exit_code=0)
    assert res["passed"] == 15
    assert res["failed"] == 0
    assert res["skipped"] == 0
    assert res["exit_code"] == 0
    assert res["success"] is True


def test_parse_test_output_with_failures():
    output = "collected 20 items\n\n2 failed, 17 passed, 1 skipped in 2.50s\n"
    res = parse_test_output(output, exit_code=1)
    assert res["passed"] == 17
    assert res["failed"] == 2
    assert res["skipped"] == 1
    assert res["exit_code"] == 1
    assert res["success"] is False


def test_parse_test_output_empty_with_nonzero_exit():
    res = parse_test_output("", exit_code=2)
    assert res["passed"] == 0
    assert res["failed"] == 1
    assert res["exit_code"] == 2
    assert res["success"] is False


def test_conclusion_clean_workspace():
    builder = WorkflowConclusionBuilder()
    c = builder.build()
    assert c["verdict"] == "CLEAN_WORKSPACE"
    assert c["is_verified"] is False
    assert "No uncommitted file modifications" in c["summary"]


def test_conclusion_unverified_modifications():
    builder = WorkflowConclusionBuilder(
        changes=[{"status": "M", "path": "app/main.py"}],
        diffs={"app/main.py": "--- a/app/main.py\n+++ b/app/main.py\n@@ -1,3 +1,4 @@\n+print(1)"},
    )
    c = builder.build()
    assert c["verdict"] == "UNVERIFIED_CHANGES"
    assert c["is_verified"] is False
    assert c["changes"]["total_files"] == 1
    assert "Verification has not been executed yet" in c["summary"]


def test_conclusion_verified_success():
    plan = {
        "taskId": "local-plan",
        "plan": {
            "objective": "Refactor workspace routers",
            "confidence": "high",
            "steps": [{"order": 1, "description": "Step 1"}],
            "task": {"type": "refactor", "description": "Refactor workspace routers"},
        },
    }
    changes = [{"status": "M", "path": "app/api/workspace.py"}]
    diffs = {"app/api/workspace.py": "+# comment\n"}
    verification = {
        "command": "pytest -q",
        "exitCode": 0,
        "output": "25 passed in 0.8s",
    }
    builder = WorkflowConclusionBuilder(
        plan=plan,
        changes=changes,
        diffs=diffs,
        verification=verification,
    )
    c = builder.build()
    assert c["verdict"] == "VERIFIED_SUCCESS"
    assert c["is_verified"] is True
    assert c["task"]["classification"] == "refactor"
    assert c["task"]["confidence"] == "high"
    assert c["verification"]["passed"] == 25
    assert "passed successfully" in c["summary"]


def test_conclusion_failed_verification_never_claims_success():
    changes = [{"status": "M", "path": "app/api/workspace.py"}]
    verification = {
        "command": "pytest -q",
        "exitCode": 1,
        "output": "1 failed, 10 passed in 1.0s",
    }
    builder = WorkflowConclusionBuilder(
        changes=changes,
        verification=verification,
    )
    c = builder.build()
    assert c["verdict"] == "VERIFICATION_FAILED"
    assert c["is_verified"] is False
    assert c["verification"]["failed"] == 1
    assert "failed" in c["summary"].lower()
