import json
import sys
from pathlib import Path

import pytest

from app.services import engineering_tools
from app.services.engineering_tools import (
    ReadFileRequest,
    ReadFileTool,
    RunCommandRequest,
    RunCommandTool,
    SearchFilesRequest,
    SearchFilesTool,
    ToolLimits,
    ToolRegistry,
    WriteFileRequest,
    WriteFileTool,
    create_default_tool_registry,
)


def assert_failure(result, code: str) -> None:
    assert result.success is False
    assert result.error is not None
    assert result.error.code == code
    json.dumps(result.to_dict())


def test_registry_discovers_tools_rejects_duplicates_and_handles_unknown_tools(
    tmp_path: Path,
):
    registry = create_default_tool_registry()

    metadata = registry.list_tools()

    assert [item.name for item in metadata] == [
        "read_file",
        "run_command",
        "search_files",
        "write_file",
    ]
    assert registry.get("read_file") is not None
    assert {
        item.input_model for item in metadata
    } == {
        "ReadFileRequest",
        "RunCommandRequest",
        "SearchFilesRequest",
        "WriteFileRequest",
    }
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ReadFileTool())

    unknown = registry.execute(
        "not_a_tool",
        ReadFileRequest(repository_root=tmp_path, path="missing.txt"),
    )

    assert_failure(unknown, "unknown_tool")


def test_tool_requests_are_validated_and_results_are_structured(tmp_path: Path):
    result = ReadFileTool().execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="file.txt",
            content="text",
        )
    )

    assert_failure(result, "validation_error")
    assert result.tool_name == "read_file"


def test_read_file_returns_text_unicode_and_metadata(tmp_path: Path):
    # Use binary write to avoid platform-specific line ending conversion
    content = "Forge ✓\n".encode("utf-8")
    (tmp_path / "notes.txt").write_bytes(content)

    result = ReadFileTool().execute(
        ReadFileRequest(repository_root=tmp_path, path="notes.txt")
    )

    assert result.success is True
    assert result.data == {
        "path": "notes.txt",
        "content": "Forge ✓\n",
        "size_bytes": len(content),
        "encoding": "utf-8",
    }


def test_read_file_rejects_missing_files_and_directories(tmp_path: Path):
    (tmp_path / "directory").mkdir()
    tool = ReadFileTool()

    missing = tool.execute(
        ReadFileRequest(repository_root=tmp_path, path="missing.txt")
    )
    directory = tool.execute(
        ReadFileRequest(repository_root=tmp_path, path="directory")
    )

    assert_failure(missing, "file_not_found")
    assert_failure(directory, "not_a_file")


def test_read_file_handles_decode_and_size_failures_without_partial_content(
    tmp_path: Path,
):
    (tmp_path / "binary.dat").write_bytes(b"\xff\xfe")
    (tmp_path / "large.txt").write_text("x" * 11, encoding="utf-8")
    tool = ReadFileTool(ToolLimits(max_read_bytes=10))

    decode_failure = tool.execute(
        ReadFileRequest(repository_root=tmp_path, path="binary.dat")
    )
    size_failure = tool.execute(
        ReadFileRequest(repository_root=tmp_path, path="large.txt")
    )

    assert_failure(decode_failure, "decode_error")
    assert_failure(size_failure, "size_limit_exceeded")
    assert "content" not in size_failure.data
    assert size_failure.data["max_bytes"] == 10


def test_read_file_rejects_traversal_absolute_paths_and_symlink_escapes(
    tmp_path: Path,
):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "outside-link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are unavailable in this environment")

    tool = ReadFileTool()
    traversal = tool.execute(
        ReadFileRequest(repository_root=tmp_path, path="../outside.txt")
    )
    absolute = tool.execute(
        ReadFileRequest(repository_root=tmp_path, path=str(outside))
    )
    symlink = tool.execute(
        ReadFileRequest(repository_root=tmp_path, path="outside-link.txt")
    )

    assert_failure(traversal, "path_violation")
    assert_failure(absolute, "path_violation")
    assert_failure(symlink, "path_violation")


def test_search_files_returns_sorted_matches_with_lines_snippets_and_case_modes(
    tmp_path: Path,
):
    (tmp_path / "nested").mkdir()
    (tmp_path / "b.txt").write_text("Forge\nforge\n", encoding="utf-8")
    (tmp_path / "nested" / "a.txt").write_text(
        "before forge after\n",
        encoding="utf-8",
    )
    tool = SearchFilesTool()

    insensitive = tool.execute(
        SearchFilesRequest(repository_root=tmp_path, query="forge")
    )
    sensitive = tool.execute(
        SearchFilesRequest(
            repository_root=tmp_path,
            query="forge",
            case_sensitive=True,
        )
    )

    assert insensitive.success is True
    assert [
        (match["path"], match["line"], match["column"], match["snippet"])
        for match in insensitive.data["matches"]
    ] == [
        ("b.txt", 1, 1, "Forge"),
        ("b.txt", 2, 1, "forge"),
        ("nested/a.txt", 1, 8, "before forge after"),
    ]
    assert [(match["path"], match["line"]) for match in sensitive.data["matches"]] == [
        ("b.txt", 2),
        ("nested/a.txt", 1),
    ]


def test_search_files_supports_no_matches_filters_and_result_limits(tmp_path: Path):
    (tmp_path / "a.py").write_text("needle\nneedle\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("needle\n", encoding="utf-8")
    tool = SearchFilesTool()

    no_match = tool.execute(
        SearchFilesRequest(repository_root=tmp_path, query="missing")
    )
    filtered = tool.execute(
        SearchFilesRequest(
            repository_root=tmp_path,
            query="needle",
            include_patterns=("*.py",),
            max_results=2,
        )
    )

    assert no_match.success is True
    assert no_match.data["matches"] == []
    assert filtered.success is True
    assert filtered.data["match_count"] == 2
    assert filtered.data["result_limit_reached"] is True
    assert {match["path"] for match in filtered.data["matches"]} == {"a.py"}


def test_search_files_skips_ignored_binary_and_oversized_files(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "Git").mkdir()
    (tmp_path / ".git" / "hidden.txt").write_text("needle", encoding="utf-8")
    (tmp_path / ".venv" / "hidden.txt").write_text("needle", encoding="utf-8")
    (tmp_path / "Git" / "hidden.txt").write_text("needle", encoding="utf-8")
    (tmp_path / "binary.dat").write_bytes(b"needle\x00")
    (tmp_path / "large.txt").write_text("needle" * 4, encoding="utf-8")
    (tmp_path / "visible.txt").write_text("needle", encoding="utf-8")
    tool = SearchFilesTool(ToolLimits(max_search_file_bytes=10))

    result = tool.execute(
        SearchFilesRequest(repository_root=tmp_path, query="needle")
    )

    assert result.success is True
    assert [match["path"] for match in result.data["matches"]] == ["visible.txt"]
    assert result.data["skipped"] == {
        "binary": 1,
        "oversized": 1,
        "unreadable": 0,
    }


def test_search_files_validates_regex_and_avoids_symlink_escapes(tmp_path: Path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-search.txt"
    outside.write_text("needle", encoding="utf-8")
    link = tmp_path / "outside-link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are unavailable in this environment")

    tool = SearchFilesTool()
    invalid_regex = tool.execute(
        SearchFilesRequest(repository_root=tmp_path, query="(", regex=True)
    )
    search = tool.execute(
        SearchFilesRequest(repository_root=tmp_path, query="needle")
    )

    assert_failure(invalid_regex, "validation_error")
    assert search.success is True
    assert search.data["matches"] == []


def test_write_file_creates_unicode_nested_and_explicitly_overwrites(tmp_path: Path):
    tool = WriteFileTool()

    created = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="nested/notes.txt",
            content="Forge ✓",
            create_parents=True,
        )
    )
    blocked_overwrite = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="nested/notes.txt",
            content="new",
        )
    )
    overwritten = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="nested/notes.txt",
            content="new",
            overwrite=True,
        )
    )

    assert created.success is True
    assert created.data["created"] is True
    assert_failure(blocked_overwrite, "file_exists")
    assert overwritten.success is True
    assert overwritten.data["overwritten"] is True
    assert (tmp_path / "nested" / "notes.txt").read_text(encoding="utf-8") == "new"


def test_write_file_rejects_size_and_unsafe_paths_without_modifying_outside(
    tmp_path: Path,
):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-write.txt"
    outside.write_text("outside", encoding="utf-8")
    tool = WriteFileTool(ToolLimits(max_write_bytes=5))

    oversized = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="large.txt",
            content="sixsix",
        )
    )
    traversal = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="../outside-write.txt",
            content="changed",
        )
    )
    absolute = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path=str(outside),
            content="changed",
        )
    )

    assert_failure(oversized, "size_limit_exceeded")
    assert_failure(traversal, "path_violation")
    assert_failure(absolute, "path_violation")
    assert outside.read_text(encoding="utf-8") == "outside"


def test_write_file_rejects_symlink_writes_and_preserves_existing_file_on_failure(
    tmp_path: Path,
    monkeypatch,
):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-write-link.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "outside-link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are unavailable in this environment")

    tool = WriteFileTool()
    symlink = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="outside-link.txt",
            content="changed",
            overwrite=True,
        )
    )
    target = tmp_path / "target.txt"
    target.write_text("original", encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(engineering_tools.os, "replace", fail_replace)
    failed_replace = tool.execute(
        WriteFileRequest(
            repository_root=tmp_path,
            path="target.txt",
            content="replacement",
            overwrite=True,
        )
    )

    assert_failure(symlink, "path_violation")
    assert outside.read_text(encoding="utf-8") == "outside"
    assert_failure(failed_replace, "io_error")
    assert target.read_text(encoding="utf-8") == "original"


def write_probe_test(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_run_command_captures_success_output_stderr_and_repository_cwd(
    tmp_path: Path,
):
    write_probe_test(
        tmp_path / "probe.py",
        "from pathlib import Path\n"
        "import sys\n"
        "\n"
        "def test_probe():\n"
        "    print('stdout marker')\n"
        "    print('stderr marker', file=sys.stderr)\n"
        "    assert Path.cwd() == Path(__file__).parent\n",
    )

    result = RunCommandTool().execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command=sys.executable,
            arguments=("-m", "pytest", "-q", "-s", "probe.py"),
            timeout_seconds=30,
        )
    )

    assert result.success is True
    assert result.data["exit_code"] == 0
    assert result.data["timed_out"] is False
    assert result.data["stdout_truncated"] is False
    assert result.data["stderr_truncated"] is False
    assert "stdout marker" in result.data["stdout"]
    assert "stderr marker" in result.data["stderr"]


def test_run_command_reports_nonzero_timeout_output_limits_and_invalid_commands(
    tmp_path: Path,
):
    write_probe_test(
        tmp_path / "failing.py",
        "def test_failure():\n"
        "    assert False\n",
    )
    write_probe_test(
        tmp_path / "slow.py",
        "import time\n"
        "\n"
        "def test_slow():\n"
        "    time.sleep(5)\n",
    )
    write_probe_test(
        tmp_path / "loud.py",
        "def test_loud():\n"
        "    print('x' * 512)\n",
    )
    tool = RunCommandTool(
        ToolLimits(
            default_command_timeout_seconds=1,
            max_command_timeout_seconds=30,
            max_command_output_bytes=64,
        )
    )

    nonzero = tool.execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command=sys.executable,
            arguments=("-m", "pytest", "-q", "failing.py"),
            timeout_seconds=30,
        )
    )
    timeout = tool.execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command=sys.executable,
            arguments=("-m", "pytest", "-q", "slow.py"),
            timeout_seconds=0.1,
        )
    )
    output_limited = tool.execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command=sys.executable,
            arguments=("-m", "pytest", "-q", "-s", "loud.py"),
            timeout_seconds=30,
        )
    )
    invalid = tool.execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command="forge-command-that-does-not-exist",
        )
    )

    assert_failure(nonzero, "command_failed")
    assert nonzero.data["exit_code"] != 0
    assert_failure(timeout, "timeout")
    assert timeout.data["timed_out"] is True
    assert output_limited.success is True
    assert output_limited.data["stdout_truncated"] is True
    assert len(output_limited.data["stdout"].encode("utf-8")) <= 64
    assert_failure(invalid, "command_not_found")


def test_run_command_rejects_direct_python_source_escape_arguments_and_timeout(
    tmp_path: Path,
):
    tool = RunCommandTool()

    direct_python = tool.execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command=sys.executable,
            arguments=("-c", "print('not run')"),
        )
    )
    escaped_argument = tool.execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command="pytest",
            arguments=("../outside.py",),
        )
    )
    excessive_timeout = tool.execute(
        RunCommandRequest(
            repository_root=tmp_path,
            command="pytest",
            timeout_seconds=1_000,
        )
    )

    assert_failure(direct_python, "validation_error")
    assert_failure(escaped_argument, "validation_error")
    assert_failure(excessive_timeout, "validation_error")
