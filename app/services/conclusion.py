"""Deterministic engineering workflow conclusion generator for Forge.

Synthesizes evidence across all workflow stages:
UNDERSTAND -> INVESTIGATE -> PLAN -> INSPECT -> MODIFY -> REVIEW -> VERIFY -> CONCLUDE.
Communicates results honestly without assuming success.
"""

from __future__ import annotations

import re
from typing import Any


def parse_test_output(output: str, exit_code: int) -> dict[str, Any]:
    """Parse deterministic metrics from pytest command output."""
    if not output:
        return {
            "passed": 0,
            "failed": 1 if exit_code != 0 else 0,
            "skipped": 0,
            "exit_code": exit_code,
            "success": exit_code == 0,
        }

    passed_match = re.search(r"(\d+)\s+passed", output)
    failed_match = re.search(r"(\d+)\s+failed", output)
    skipped_match = re.search(r"(\d+)\s+skipped", output)

    passed = int(passed_match.group(1)) if passed_match else 0
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    if failed_match:
        failed = int(failed_match.group(1))
    else:
        failed = 1 if exit_code != 0 else 0

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "exit_code": exit_code,
        "success": exit_code == 0 and failed == 0,
    }


class WorkflowConclusionBuilder:
    """Build an evidence-backed conclusion from active workflow state."""

    def __init__(
        self,
        *,
        plan: dict[str, Any] | None = None,
        changes: list[dict[str, str]] | None = None,
        diffs: dict[str, str] | None = None,
        verification: dict[str, Any] | None = None,
    ) -> None:
        self.plan = plan
        self.changes = changes or []
        self.diffs = diffs or {}
        self.verification = verification

    def build(self) -> dict[str, Any]:
        """Synthesize workflow evidence into an honest conclusion."""
        # 1. Task evidence
        task_data = None
        if self.plan:
            plan_obj = self.plan.get("plan", self.plan)
            task_obj = plan_obj.get("task", {})
            task_data = {
                "objective": plan_obj.get("objective") or task_obj.get("description", "Unnamed task"),
                "classification": task_obj.get("type") or self.plan.get("classification", "general"),
                "confidence": plan_obj.get("confidence") or self.plan.get("confidence", "unrated"),
                "steps_count": len(plan_obj.get("steps", [])),
                "affected_files": plan_obj.get("affected_files", []),
                "risks_count": len(plan_obj.get("risks", [])),
            }

        # 2. Changes evidence
        change_files = [c.get("path", "") for c in self.changes if c.get("path")]
        changes_data = {
            "total_files": len(change_files),
            "files": change_files,
            "has_changes": len(change_files) > 0,
            "diff_summary": {
                path: {
                    "additions": diff.count("\n+") - diff.count("\n+++"),
                    "deletions": diff.count("\n-") - diff.count("\n---"),
                    "lines": len(diff.splitlines()),
                }
                for path, diff in self.diffs.items()
                if diff
            },
        }

        # 3. Verification evidence
        verification_data = None
        if self.verification:
            cmd = self.verification.get("command", "pytest -q")
            exit_code = int(self.verification.get("exitCode", self.verification.get("exit_code", 1)))
            output = self.verification.get("output", "")
            metrics = parse_test_output(output, exit_code)
            verification_data = {
                "command": cmd,
                "exit_code": exit_code,
                "passed": metrics["passed"],
                "failed": metrics["failed"],
                "skipped": metrics["skipped"],
                "success": metrics["success"],
                "has_run": True,
            }

        # 4. Verdict determination
        if not changes_data["has_changes"]:
            if verification_data and not verification_data["success"]:
                verdict = "VERIFICATION_FAILED"
            elif verification_data and verification_data["success"]:
                verdict = "CLEAN_WORKSPACE_VERIFIED"
            else:
                verdict = "CLEAN_WORKSPACE"
        else:
            if not verification_data:
                verdict = "UNVERIFIED_CHANGES"
            elif verification_data["success"]:
                verdict = "VERIFIED_SUCCESS"
            else:
                verdict = "VERIFICATION_FAILED"

        # 5. Narrative summary
        summary_parts = []
        if task_data:
            summary_parts.append(
                f"Task '{task_data['objective']}' planned ({task_data['classification']}, {task_data['confidence']} confidence, {task_data['steps_count']} steps)."
            )

        if changes_data["has_changes"]:
            summary_parts.append(
                f"{changes_data['total_files']} file(s) modified: {', '.join(changes_data['files'][:5])}{'...' if len(changes_data['files']) > 5 else ''}."
            )
        else:
            summary_parts.append("No uncommitted file modifications in workspace.")

        if verification_data:
            v_status = "passed successfully" if verification_data["success"] else "failed"
            summary_parts.append(
                f"Verification command '{verification_data['command']}' {v_status} (exit code {verification_data['exit_code']}: {verification_data['passed']} passed, {verification_data['failed']} failed, {verification_data['skipped']} skipped)."
            )
        else:
            summary_parts.append("Verification has not been executed yet.")

        summary_parts.append(f"Final verdict: {verdict}.")

        return {
            "status": verdict,
            "verdict": verdict,
            "is_verified": verdict in ("VERIFIED_SUCCESS", "CLEAN_WORKSPACE_VERIFIED"),
            "summary": " ".join(summary_parts),
            "task": task_data,
            "changes": changes_data,
            "verification": verification_data,
            "stages": {
                "understand": {"status": "completed"},
                "investigate": {"status": "completed"},
                "plan": {"status": "completed" if task_data else "skipped"},
                "inspect": {"status": "completed" if changes_data["has_changes"] else "ready"},
                "modify": {"status": "completed" if changes_data["has_changes"] else "ready"},
                "review": {"status": "completed" if self.diffs else ("ready" if changes_data["has_changes"] else "clean")},
                "verify": {
                    "status": "completed" if verification_data else "pending",
                    "passed": verification_data["success"] if verification_data else False,
                },
                "conclude": {"status": "completed"},
            },
        }
