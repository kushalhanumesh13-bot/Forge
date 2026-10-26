"""Workspace management for Forge — handles user-selected workspace isolation."""
from __future__ import annotations

import os
import hashlib
from pathlib import Path
from typing import Optional

from fastapi import HTTPException


class WorkspaceManager:
    """Manages the active workspace root with validation and isolation."""

    def __init__(self, default_root: Optional[Path] = None):
        self._default_root = default_root or Path.cwd().resolve()
        self._current_root: Optional[Path] = None

    @property
    def default_root(self) -> Path:
        return self._default_root

    @property
    def current_root(self) -> Path:
        """Returns the active workspace root, or default if none selected."""
        return self._current_root or self._default_root

    @property
    def is_using_default(self) -> bool:
        return self._current_root is None

    def validate_workspace_path(self, path: Path) -> Path:
        """
        Validate a path as a suitable workspace root.
        Returns the canonical resolved path.
        """
        if not isinstance(path, Path):
            raise HTTPException(status_code=400, detail="Invalid path type")

        # Must exist
        if not path.exists():
            raise HTTPException(status_code=400, detail="Workspace path does not exist")

        # Must be a directory
        if not path.is_dir():
            raise HTTPException(status_code=400, detail="Workspace path must be a directory")

        # Must be readable
        if not os.access(path, os.R_OK):
            raise HTTPException(status_code=400, detail="Workspace path is not readable")

        # Reject if the path itself is a symlink
        if path.is_symlink():
            raise HTTPException(status_code=400, detail="Workspace path cannot be a symlink")

        # Resolve to canonical path (resolves symlinks)
        try:
            canonical = path.resolve()
        except (OSError, RuntimeError) as e:
            raise HTTPException(status_code=400, detail="Invalid workspace path") from e

        # Check for symlink traversal in the resolved path components
        # Walk from root to the path, checking each component
        try:
            relative_parts = canonical.relative_to(canonical.anchor).parts
        except ValueError:
            # On Windows, anchor might not work the same way
            relative_parts = canonical.parts[1:] if canonical.is_absolute() else canonical.parts

        current = Path(canonical.anchor) if canonical.is_absolute() else Path(".")
        for part in relative_parts:
            if part in ("", "."):
                continue
            current = current / part
            if current.is_symlink():
                raise HTTPException(status_code=400, detail="Symlink traversal not allowed in workspace path")

        return canonical

    def set_workspace(self, path: Path) -> Path:
        """Set the active workspace to the given path after validation."""
        canonical = self.validate_workspace_path(path)
        self._current_root = canonical
        return canonical

    def reset_to_default(self) -> Path:
        """Reset to the default (Forge source) workspace."""
        self._current_root = None
        return self._default_root

    def get_workspace_info(self) -> dict:
        """Get metadata about the current workspace."""
        root = self.current_root
        name = root.name or "Workspace"
        return {
            "root": str(root),
            "name": name,
            "isDefault": self.is_using_default,
        }

    def compute_workspace_id(self, path: Path) -> str:
        """Compute a stable ID for a workspace path."""
        canonical = str(path.resolve())
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# Global instance (initialized in main.py)
workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager() -> WorkspaceManager:
    """Get the global workspace manager instance."""
    global workspace_manager
    if workspace_manager is None:
        workspace_manager = WorkspaceManager()
    return workspace_manager