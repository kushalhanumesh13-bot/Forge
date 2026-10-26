"""Tests for WorkspaceManager."""
import os
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services.workspace_manager import WorkspaceManager


class TestWorkspaceManager:
    """Tests for WorkspaceManager class."""

    def test_default_root(self):
        """Test default root is current working directory."""
        manager = WorkspaceManager(Path("/tmp/default"))
        assert manager.current_root == Path("/tmp/default")
        assert manager.is_using_default is True

    def test_set_workspace_valid(self, tmp_path):
        """Test setting a valid workspace."""
        manager = WorkspaceManager(tmp_path)
        test_workspace = tmp_path / "test_project"
        test_workspace.mkdir()

        result = manager.set_workspace(test_workspace)

        assert result == test_workspace.resolve()
        assert manager.current_root == test_workspace.resolve()
        assert manager.is_using_default is False

    def test_set_workspace_nonexistent(self, tmp_path):
        """Test setting a nonexistent workspace raises error."""
        manager = WorkspaceManager(tmp_path)
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(HTTPException) as exc:
            manager.set_workspace(nonexistent)
        assert exc.value.status_code == 400
        assert "does not exist" in exc.value.detail

    def test_set_workspace_not_directory(self, tmp_path):
        """Test setting a file (not directory) raises error."""
        manager = WorkspaceManager(tmp_path)
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(HTTPException) as exc:
            manager.set_workspace(file_path)
        assert exc.value.status_code == 400
        assert "must be a directory" in exc.value.detail

    def test_set_workspace_symlink(self, tmp_path):
        """Test setting a symlink as workspace raises error."""
        manager = WorkspaceManager(tmp_path)
        target = tmp_path / "real_dir"
        target.mkdir()
        link = tmp_path / "link_dir"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported")

        with pytest.raises(HTTPException) as exc:
            manager.set_workspace(link)
        assert exc.value.status_code == 400
        assert "cannot be a symlink" in exc.value.detail

    def test_reset_to_default(self, tmp_path):
        """Test resetting to default workspace."""
        manager = WorkspaceManager(tmp_path)
        test_workspace = tmp_path / "test_project"
        test_workspace.mkdir()

        manager.set_workspace(test_workspace)
        assert manager.is_using_default is False

        result = manager.reset_to_default()

        assert result == tmp_path
        assert manager.current_root == tmp_path
        assert manager.is_using_default is True

    def test_get_workspace_info(self, tmp_path):
        """Test getting workspace info."""
        manager = WorkspaceManager(tmp_path)
        test_workspace = tmp_path / "my_project"
        test_workspace.mkdir()

        manager.set_workspace(test_workspace)
        info = manager.get_workspace_info()

        assert info["root"] == str(test_workspace.resolve())
        assert info["name"] == "my_project"
        assert info["isDefault"] is False

    def test_compute_workspace_id(self, tmp_path):
        """Test workspace ID computation is stable."""
        manager = WorkspaceManager(tmp_path)
        test_workspace = tmp_path / "project"
        test_workspace.mkdir()

        id1 = manager.compute_workspace_id(test_workspace)
        id2 = manager.compute_workspace_id(test_workspace)

        assert id1 == id2
        assert len(id1) == 16  # SHA256 truncated to 16 chars

    def test_validate_workspace_path_rejects_symlink_in_path(self, tmp_path):
        """Test that symlinks in path components are rejected."""
        manager = WorkspaceManager(tmp_path)

        # Create a real directory
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        # Create a symlink inside it
        link_inside = real_dir / "link"
        try:
            (tmp_path / "outside").mkdir()
            link_inside.symlink_to(tmp_path / "outside")
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported")

        # Try to validate a path that goes through the symlink
        with pytest.raises(HTTPException) as exc:
            manager.validate_workspace_path(link_inside)
        assert exc.value.status_code == 400
        assert "Symlink traversal" in exc.value.detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])