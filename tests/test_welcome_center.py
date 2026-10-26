"""Tests for Welcome Center API endpoints and workspace switching."""
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestWorkspaceAPI:
    """Tests for workspace selection API endpoints."""

    def test_get_current_workspace_default(self):
        """Test getting current workspace when using default."""
        response = client.get("/api/workspace/current")
        assert response.status_code == 200
        data = response.json()
        assert "root" in data
        assert "name" in data
        assert "isDefault" in data
        assert data["isDefault"] is True

    def test_select_workspace_valid(self, tmp_path):
        """Test selecting a valid workspace."""
        test_workspace = tmp_path / "test_project"
        test_workspace.mkdir()

        response = client.post("/api/workspace/select", json={"path": str(test_workspace)})
        assert response.status_code == 200
        data = response.json()
        assert data["root"] == str(test_workspace.resolve())
        assert data["name"] == "test_project"
        assert data["isDefault"] is False

        # Verify current workspace changed
        current = client.get("/api/workspace/current")
        assert current.json()["isDefault"] is False
        assert current.json()["root"] == str(test_workspace.resolve())

    def test_select_workspace_nonexistent(self):
        """Test selecting a nonexistent workspace fails."""
        response = client.post("/api/workspace/select", json={"path": "/nonexistent/path"})
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]

    def test_select_workspace_not_directory(self, tmp_path):
        """Test selecting a file (not directory) fails."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        response = client.post("/api/workspace/select", json={"path": str(file_path)})
        assert response.status_code == 400
        assert "must be a directory" in response.json()["detail"]

    def test_reset_workspace(self, tmp_path):
        """Test resetting to default workspace."""
        # First select a different workspace
        test_workspace = tmp_path / "test_project"
        test_workspace.mkdir()
        client.post("/api/workspace/select", json={"path": str(test_workspace)})

        # Now reset
        response = client.post("/api/workspace/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["isDefault"] is True

        # Verify current workspace is default
        current = client.get("/api/workspace/current")
        assert current.json()["isDefault"] is True

    def test_workspace_isolation_file_read(self, tmp_path):
        """Test that file reads are isolated to the current workspace."""
        # Create two workspaces with different files
        ws1 = tmp_path / "ws1"
        ws1.mkdir()
        (ws1 / "file1.txt").write_text("content from ws1")

        ws2 = tmp_path / "ws2"
        ws2.mkdir()
        (ws2 / "file2.txt").write_text("content from ws2")

        # Select ws1 and read file
        client.post("/api/workspace/select", json={"path": str(ws1)})
        response = client.get("/api/file?path=file1.txt")
        assert response.status_code == 200
        assert response.json()["content"] == "content from ws1"

        # Select ws2 and try to read ws1's file - should fail
        client.post("/api/workspace/select", json={"path": str(ws2)})
        response = client.get("/api/file?path=file1.txt")
        assert response.status_code == 404

    def test_workspace_isolation_git_changes(self, tmp_path):
        """Test that Git changes are isolated to the current workspace."""
        # Create a workspace with git repo
        ws1 = tmp_path / "ws1"
        ws1.mkdir()

        # Initialize git
        import subprocess
        subprocess.run(["git", "init"], cwd=ws1, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=ws1, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=ws1, capture_output=True)
        (ws1 / "file.txt").write_text("initial")
        subprocess.run(["git", "add", "file.txt"], cwd=ws1, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=ws1, capture_output=True)

        # Select ws1
        client.post("/api/workspace/select", json={"path": str(ws1)})

        # Get changes - should be clean
        response = client.get("/api/changes")
        assert response.status_code == 200
        assert len(response.json()["changes"]) == 0

    def test_select_workspace_resets_workflow_state(self, tmp_path):
        """Test that selecting a workspace resets the active plan and verification."""
        # Submit a task first (using default workspace)
        client.post("/api/task/submit", json={"description": "Test task"})
        plan = client.get("/api/task/plan")
        assert plan.json()["status"] == "complete"

        # Select new workspace
        test_workspace = tmp_path / "test_project"
        test_workspace.mkdir()
        client.post("/api/workspace/select", json={"path": str(test_workspace)})

        # Plan should be reset
        plan = client.get("/api/task/plan")
        assert plan.json()["status"] == "empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])