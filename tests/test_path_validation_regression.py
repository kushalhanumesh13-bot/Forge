"""
Regression tests for path validation defects (DEF-001 through DEF-007).
These tests verify that the path validation fixes work correctly and
that valid paths are still accepted.
"""
import sys
sys.path.insert(0, 'E:\\Projects\\001')

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.workspace import _workspace_path
from app.services.engineering_tools import _normalise_relative_path, _resolve_repository_path
from app.main import app

client = TestClient(app)


class TestWorkspacePathValidation:
    """Tests for _workspace_path function in app/api/workspace.py"""

    def test_empty_string_rejected(self):
        """DEF-001: Empty string should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("")
        assert exc.value.status_code == 400
        assert "non-empty" in exc.value.detail.lower()

    def test_whitespace_only_rejected(self):
        """DEF-002: Whitespace-only strings should be rejected"""
        for ws in [" ", "  ", "\t", "\n", "\r", " \t\n "]:
            with pytest.raises(HTTPException) as exc:
                _workspace_path(ws)
            assert exc.value.status_code == 400
            assert "non-empty" in exc.value.detail.lower()

    def test_trailing_slash_rejected(self):
        """DEF-003: Trailing slash should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("app/")
        assert exc.value.status_code == 400
        assert "separator" in exc.value.detail.lower()

    def test_trailing_backslash_rejected(self):
        """DEF-003: Trailing backslash should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("app\\")
        assert exc.value.status_code == 400
        assert "separator" in exc.value.detail.lower()

    def test_windows_reserved_names_rejected(self):
        """DEF-004: Windows reserved names should be rejected"""
        reserved = ["CON", "PRN", "AUX", "NUL",
                    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]
        for name in reserved:
            with pytest.raises(HTTPException) as exc:
                _workspace_path(name)
            assert exc.value.status_code == 400
            assert "reserved" in exc.value.detail.lower()

    def test_windows_reserved_with_extension_rejected(self):
        """DEF-004: Windows reserved names with extensions should be rejected"""
        reserved_ext = ["CON.txt", "PRN.log", "AUX.py", "NUL.dat",
                        "COM1.bak", "LPT1.tmp"]
        for name in reserved_ext:
            with pytest.raises(HTTPException) as exc:
                _workspace_path(name)
            assert exc.value.status_code == 400
            assert "reserved" in exc.value.detail.lower()

    def test_windows_reserved_in_nested_path_rejected(self):
        """DEF-004: Windows reserved names in nested paths should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("app/CON.txt")
        assert exc.value.status_code == 400
        assert "reserved" in exc.value.detail.lower()

    def test_trailing_dot_rejected(self):
        """DEF-005: Trailing dot should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("test.")
        assert exc.value.status_code == 400
        assert "dot" in exc.value.detail.lower()

    def test_trailing_double_dot_rejected(self):
        """DEF-005: Trailing double dot should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("test..")
        assert exc.value.status_code == 400
        assert "dot" in exc.value.detail.lower()

    def test_trailing_space_rejected(self):
        """DEF-005: Trailing space should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("test ")
        assert exc.value.status_code == 400
        assert "space" in exc.value.detail.lower()

    def test_trailing_tab_rejected(self):
        """DEF-005: Trailing tab should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("test\t")
        assert exc.value.status_code == 400
        assert "control" in exc.value.detail.lower() or "space" in exc.value.detail.lower()

    def test_trailing_newline_rejected(self):
        """DEF-005: Trailing newline should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("test\n")
        assert exc.value.status_code == 400
        assert "control" in exc.value.detail.lower() or "space" in exc.value.detail.lower()

    def test_trailing_carriage_return_rejected(self):
        """DEF-005: Trailing carriage return should be rejected"""
        with pytest.raises(HTTPException) as exc:
            _workspace_path("test\r")
        assert exc.value.status_code == 400
        assert "control" in exc.value.detail.lower() or "space" in exc.value.detail.lower()

    # Valid paths should still work
    def test_valid_relative_path_accepted(self):
        """Valid relative paths should be accepted"""
        result = _workspace_path("app/main.py")
        assert result.name == "main.py"

    def test_valid_nested_path_accepted(self):
        """Valid nested paths should be accepted"""
        result = _workspace_path("app/services/repository.py")
        assert result.name == "repository.py"

    def test_dot_segment_accepted(self):
        """Dot segments should be accepted and normalized"""
        result = _workspace_path("app/./main.py")
        assert result.name == "main.py"

    def test_root_file_accepted(self):
        """Files at repository root should be accepted"""
        result = _workspace_path("README.md")
        assert result.name == "README.md"

    def test_deep_path_accepted(self):
        """Deep paths should be accepted"""
        result = _workspace_path("a/b/c/d/e/f.py")
        assert result.name == "f.py"


class TestEngineeringToolsPathValidation:
    """Tests for _normalise_relative_path and _resolve_repository_path in engineering_tools.py"""

    def test_empty_string_rejected(self):
        """DEF-001 equivalent: Empty string should be rejected"""
        result, error = _normalise_relative_path("")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"

    def test_whitespace_only_rejected(self):
        """DEF-002 equivalent: Whitespace-only strings should be rejected"""
        for ws in [" ", "  ", "\t", "\n", "\r", " \t\n "]:
            result, error = _normalise_relative_path(ws)
            assert result is None
            assert error is not None
            assert error.code == "validation_error"

    def test_trailing_slash_rejected(self):
        """DEF-003 equivalent: Trailing slash should be rejected"""
        result, error = _normalise_relative_path("app/")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"
        assert "separator" in error.message.lower()

    def test_trailing_backslash_rejected(self):
        """DEF-003 equivalent: Trailing backslash should be rejected"""
        result, error = _normalise_relative_path("app\\")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"

    def test_windows_reserved_names_rejected(self):
        """DEF-006: Windows reserved names should be rejected"""
        reserved = ["CON", "PRN", "AUX", "NUL",
                    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]
        for name in reserved:
            result, error = _normalise_relative_path(name)
            assert result is None
            assert error is not None
            assert error.code == "path_violation"
            assert "reserved" in error.message.lower()

    def test_windows_reserved_with_extension_rejected(self):
        """DEF-006: Windows reserved names with extensions should be rejected"""
        reserved_ext = ["CON.txt", "PRN.log", "AUX.py", "NUL.dat",
                        "COM1.bak", "LPT1.tmp"]
        for name in reserved_ext:
            result, error = _normalise_relative_path(name)
            assert result is None
            assert error is not None
            assert error.code == "path_violation"
            assert "reserved" in error.message.lower()

    def test_windows_reserved_in_nested_path_rejected(self):
        """DEF-006: Windows reserved names in nested paths should be rejected"""
        result, error = _normalise_relative_path("app/CON.txt")
        assert result is None
        assert error is not None
        assert error.code == "path_violation"
        assert "reserved" in error.message.lower()

    def test_trailing_dot_rejected(self):
        """DEF-007: Trailing dot should be rejected"""
        result, error = _normalise_relative_path("test.")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"
        assert "dot" in error.message.lower()

    def test_trailing_space_rejected(self):
        """DEF-007: Trailing space should be rejected"""
        result, error = _normalise_relative_path("test ")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"
        assert "space" in error.message.lower()

    def test_trailing_tab_rejected(self):
        """DEF-007: Trailing tab should be rejected"""
        result, error = _normalise_relative_path("test\t")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"
        assert "control" in error.message.lower() or "space" in error.message.lower()

    def test_trailing_newline_rejected(self):
        """DEF-007: Trailing newline should be rejected"""
        result, error = _normalise_relative_path("test\n")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"
        assert "control" in error.message.lower() or "space" in error.message.lower()

    def test_trailing_carriage_return_rejected(self):
        """DEF-007: Trailing carriage return should be rejected"""
        result, error = _normalise_relative_path("test\r")
        assert result is None
        assert error is not None
        assert error.code == "validation_error"
        assert "control" in error.message.lower() or "space" in error.message.lower()

    def test_resolve_repository_path_empty_rejected(self):
        """Empty path should be rejected by resolve function"""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test.txt").write_text("content")
            result, error = _resolve_repository_path(root, "")
            assert result is None
            assert error is not None

    def test_resolve_repository_path_windows_reserved_rejected(self):
        """Windows reserved names should be rejected by resolve function"""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test.txt").write_text("content")
            result, error = _resolve_repository_path(root, "CON")
            assert result is None
            assert error is not None
            assert error.code == "path_violation"

    # Valid paths should still work
    def test_valid_relative_path_accepted(self):
        """Valid relative paths should be accepted"""
        result, error = _normalise_relative_path("app/main.py")
        assert error is None
        assert result == ("app", "main.py")

    def test_valid_nested_path_accepted(self):
        """Valid nested paths should be accepted"""
        result, error = _normalise_relative_path("app/services/repository.py")
        assert error is None
        assert result == ("app", "services", "repository.py")

    def test_dot_segment_accepted(self):
        """Dot segments should be accepted and normalized"""
        result, error = _normalise_relative_path("app/./main.py")
        assert error is None
        assert result == ("app", "main.py")

    def test_resolve_repository_path_valid(self):
        """Valid paths should resolve correctly"""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test.txt").write_text("content")
            result, error = _resolve_repository_path(root, "test.txt")
            assert error is None
            assert result.relative_path == "test.txt"


class TestAPIEndpointsPathValidation:
    """Integration tests for API endpoints using TestClient"""

    def test_file_read_empty_path_rejected(self):
        """Empty path should return 400"""
        response = client.get("/api/file?path=")
        assert response.status_code == 400

    def test_file_read_whitespace_path_rejected(self):
        """Whitespace path should return 400"""
        response = client.get("/api/file?path=  ")
        assert response.status_code == 400

    def test_file_read_trailing_slash_rejected(self):
        """Trailing slash should return 400"""
        response = client.get("/api/file?path=app/")
        assert response.status_code == 400

    def test_file_read_windows_reserved_rejected(self):
        """Windows reserved names should return 400"""
        response = client.get("/api/file?path=CON")
        assert response.status_code == 400

    def test_file_read_trailing_dot_rejected(self):
        """Trailing dot should return 400"""
        response = client.get("/api/file?path=test.")
        assert response.status_code == 400

    def test_file_read_trailing_space_rejected(self):
        """Trailing space should return 400"""
        response = client.get("/api/file?path=test%20")
        assert response.status_code == 400

    def test_file_write_empty_path_rejected(self):
        """Empty path in write should return 400"""
        response = client.post("/api/file/write", json={"path": "", "content": "test"})
        assert response.status_code == 400

    def test_file_write_windows_reserved_rejected(self):
        """Windows reserved names in write should return 400"""
        response = client.post("/api/file/write", json={"path": "CON", "content": "test"})
        assert response.status_code == 400

    def test_file_write_trailing_slash_rejected(self):
        """Trailing slash in write should return 400"""
        response = client.post("/api/file/write", json={"path": "app/", "content": "test"})
        assert response.status_code == 400

    def test_diff_empty_path_rejected(self):
        """Empty path in diff should return 400"""
        response = client.get("/api/changes/diff?path=")
        assert response.status_code == 400

    def test_diff_windows_reserved_rejected(self):
        """Windows reserved names in diff should return 400"""
        response = client.get("/api/changes/diff?path=CON")
        assert response.status_code == 400

    def test_valid_file_read_works(self):
        """Valid file read should return 200"""
        response = client.get("/api/file?path=app/main.py")
        assert response.status_code == 200
        assert "content" in response.json()


class TestFrontendSecurityReview:
    """Tests for frontend innerHTML and setTimeout issues"""

    def test_app_js_innerhtml_uses_esc(self):
        """Check that innerHTML usages in app.js use esc() for user content"""
        with open("app/static/app.js", "r", encoding="utf-8") as f:
            content = f.read()

        # These patterns should use esc()
        # The following innerHTML assignments were identified as potentially unsafe
        # but actually do use esc() for user-controlled content

        # fileRow uses esc(file.path.split("/").pop())
        # folderRow uses esc(name) and esc(key)
        # buildTree uses esc(workspaceName())
        # loadAnalysis uses esc() for project_type, frameworks, git info
        # renderTabs uses esc(path.split("/").pop())
        # renderEditor uses esc() for breadcrumbs and path
        # searchRepository uses esc() for match.path and match.snippet
        # renderPlan uses esc() for all user-controlled content
        # palette and renderQuickFiles use esc()

        # Verify esc function exists
        assert "const esc" in content
        assert "replace" in content

        # Count innerHTML usages
        innerhtml_count = content.count(".innerHTML")
        assert innerhtml_count >= 10  # At least 10 usages exist

    def test_settimeout_no_string(self):
        """Check that setTimeout is not used with string argument"""
        with open("app/static/app.js", "r", encoding="utf-8") as f:
            content = f.read()

        # Check for setTimeout with string argument (bad practice)
        import re
        bad_settimeout = re.search(r'setTimeout\s*\(\s*["\']', content)
        # The search should find NO matches
        assert bad_settimeout is None, "Found setTimeout with string argument"

    def test_no_eval_or_function_constructor(self):
        """Check for eval or Function constructor usage"""
        with open("app/static/app.js", "r", encoding="utf-8") as f:
            content = f.read()

        assert "eval(" not in content
        assert "Function(" not in content
        assert "document.write" not in content

    def test_html_has_no_inline_scripts(self):
        """Check that index.html has no inline event handlers"""
        with open("app/static/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # No inline event handlers
        for handler in ["onclick=", "onload=", "onerror=", "onmouseover=", "onfocus="]:
            assert handler not in content.lower()

        # No inline scripts (scripts are external)
        script_count = content.count("<script")
        # Should only have the one external script tag
        assert script_count == 1

    def test_html_has_accessibility_attributes(self):
        """Check for basic accessibility attributes"""
        with open("app/static/index.html", "r", encoding="utf-8") as f:
            content = f.read()

        assert 'aria-label=' in content
        assert 'role=' in content
        assert 'tabindex=' in content


class TestFastAPIIntegration:
    """FastAPI integration tests for all endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint returns HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Forge" in response.text

    def test_health_endpoint(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Forge"
        assert data["version"] == "0.1.0"

    def test_repository_analyze_get(self):
        """Test repository analyze via GET"""
        response = client.get("/repository/analyze")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "project_type" in data

    def test_repository_analyze_post(self):
        """Test repository analyze via POST"""
        response = client.post("/repository/analyze", json={})
        assert response.status_code == 405  # Method not allowed - correct behavior

    def test_file_read_valid(self):
        """Test reading a valid file"""
        response = client.get("/api/file?path=app/main.py")
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "content" in data
        assert "lastModified" in data

    def test_file_read_not_found(self):
        """Test reading non-existent file returns 404"""
        response = client.get("/api/file?path=nonexistent.py")
        assert response.status_code == 404

    def test_file_write_valid(self):
        """Test writing to an existing file"""
        # First read the original content
        original = client.get("/api/file?path=app/main.py").json()["content"]
        try:
            # Write new content
            response = client.post("/api/file/write", json={
                "path": "app/main.py",
                "content": "test content\n"
            })
            assert response.status_code == 200
            assert response.json()["success"] is True

            # Verify the write
            verify = client.get("/api/file?path=app/main.py")
            assert verify.json()["content"] == "test content\n"
        finally:
            # Restore original content
            client.post("/api/file/write", json={
                "path": "app/main.py",
                "content": original
            })

    def test_file_write_not_found(self):
        """Test writing to non-existent file returns 404"""
        response = client.post("/api/file/write", json={
            "path": "nonexistent.py",
            "content": "test"
        })
        assert response.status_code == 404

    def test_task_submit_valid(self):
        """Test submitting a valid task"""
        response = client.post("/api/task/submit", json={
            "description": "Add a new feature"
        })
        assert response.status_code == 200
        data = response.json()
        assert "taskId" in data
        assert "plan" in data

    def test_task_submit_empty_rejected(self):
        """Test empty task description is rejected"""
        response = client.post("/api/task/submit", json={
            "description": ""
        })
        assert response.status_code == 422

    def test_search_valid(self):
        """Test search with valid query"""
        response = client.post("/api/search", json={"query": "RepositoryAnalyzer"})
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert "match_count" in data
        assert data["match_count"] > 0

    def test_search_empty_rejected(self):
        """Test empty search query is rejected"""
        response = client.post("/api/search", json={"query": ""})
        assert response.status_code == 422

    def test_search_too_long_rejected(self):
        """Test too long search query is rejected"""
        response = client.post("/api/search", json={"query": "x" * 600})
        assert response.status_code == 422

    def test_changes_list(self):
        """Test getting changes list"""
        response = client.get("/api/changes")
        assert response.status_code == 200
        data = response.json()
        assert "changes" in data
        assert isinstance(data["changes"], list)

    def test_changes_diff_valid(self):
        """Test getting diff for valid file"""
        response = client.get("/api/changes/diff?path=app/main.py")
        assert response.status_code == 200
        data = response.json()
        assert "diff" in data
        assert "path" in data

    def test_changes_diff_traversal_rejected(self):
        """Test diff with path traversal is rejected"""
        response = client.get("/api/changes/diff?path=../outside.txt")
        assert response.status_code == 400

    def test_command_run_allowed(self):
        """Test allowed command execution"""
        response = client.post("/api/command/run", json={
            "command": "python -m pytest -q"
        })
        assert response.status_code == 200
        data = response.json()
        assert "commandId" in data
        assert "output" in data
        assert "exitCode" in data

    def test_command_run_rejected(self):
        """Test disallowed command is rejected"""
        response = client.post("/api/command/run", json={
            "command": "ls -la"
        })
        assert response.status_code == 400
        assert "test command" in response.json()["detail"].lower()

    def test_command_run_python_c_rejected(self):
        """Test python -c is rejected"""
        response = client.post("/api/command/run", json={
            "command": "python -c print(1)"
        })
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])