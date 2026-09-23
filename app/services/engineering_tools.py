"""Controlled, bounded engineering operations for a local Forge workspace.

This module deliberately exposes small, typed primitives rather than an
autonomous execution loop.  It is intentionally independent of the
engineering brain and does not perform approval, diff, Git, AI, or sandboxing
work from later Forge phases.
"""

from __future__ import annotations

import codecs
import fnmatch
import math
import os
import re
import subprocess
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, ClassVar, Generic, TypeVar

from app.services.repository import RepositoryService


DEFAULT_MAX_FILE_BYTES = 1 * 1024 * 1024
DEFAULT_MAX_SEARCH_RESULTS = 100
DEFAULT_COMMAND_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_COMMAND_TIMEOUT_SECONDS = 300.0
DEFAULT_MAX_COMMAND_OUTPUT_BYTES = 1 * 1024 * 1024
DEFAULT_MAX_SNIPPET_CHARS = 1_000
MAX_QUERY_CHARS = 512
MAX_FILTER_CHARS = 512
MAX_COMMAND_CHARS = 1_024
MAX_COMMAND_ARGUMENTS = 128
MAX_COMMAND_ARGUMENT_CHARS = 4_096


@dataclass(frozen=True, slots=True)
class ToolLimits:
    """Explicit resource bounds shared by the engineering tools."""

    max_read_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_write_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_search_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_search_results: int = DEFAULT_MAX_SEARCH_RESULTS
    max_snippet_chars: int = DEFAULT_MAX_SNIPPET_CHARS
    default_command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS
    max_command_timeout_seconds: float = DEFAULT_MAX_COMMAND_TIMEOUT_SECONDS
    max_command_output_bytes: int = DEFAULT_MAX_COMMAND_OUTPUT_BYTES

    def __post_init__(self) -> None:
        integer_limits = (
            self.max_read_bytes,
            self.max_write_bytes,
            self.max_search_file_bytes,
            self.max_search_results,
            self.max_snippet_chars,
            self.max_command_output_bytes,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in integer_limits
        ):
            raise ValueError("Tool byte and count limits must be positive integers.")
        if (
            isinstance(self.default_command_timeout_seconds, bool)
            or isinstance(self.max_command_timeout_seconds, bool)
            or not isinstance(
                self.default_command_timeout_seconds,
                (int, float),
            )
            or not isinstance(
                self.max_command_timeout_seconds,
                (int, float),
            )
            or not math.isfinite(self.default_command_timeout_seconds)
            or not math.isfinite(self.max_command_timeout_seconds)
            or self.default_command_timeout_seconds <= 0
            or self.max_command_timeout_seconds <= 0
            or self.default_command_timeout_seconds
            > self.max_command_timeout_seconds
        ):
            raise ValueError("Command timeout limits must be positive and ordered.")


@dataclass(frozen=True, slots=True)
class ToolError:
    """Machine-readable, non-traceback failure information."""

    code: str
    message: str
    details: dict[str, str | int | float | bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Common structured result returned by every engineering tool."""

    success: bool
    tool_name: str
    data: dict[str, Any] = field(default_factory=dict)
    error: ToolError | None = None
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        tool_name: str,
        data: dict[str, Any] | None = None,
        *,
        metadata: dict[str, str | int | float | bool] | None = None,
    ) -> ToolResult:
        return cls(
            success=True,
            tool_name=tool_name,
            data=dict(data or {}),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def fail(
        cls,
        tool_name: str,
        code: str,
        message: str,
        *,
        data: dict[str, Any] | None = None,
        details: dict[str, str | int | float | bool] | None = None,
        metadata: dict[str, str | int | float | bool] | None = None,
    ) -> ToolResult:
        return cls(
            success=False,
            tool_name=tool_name,
            data=dict(data or {}),
            error=ToolError(code, message, dict(details or {})),
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "data": dict(self.data),
            "error": self.error.to_dict() if self.error else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    """Stable discovery metadata for a tool registry."""

    name: str
    description: str
    input_model: str
    output_model: str = "ToolResult"

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "input_model": self.input_model,
            "output_model": self.output_model,
        }


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """Base request shared by all workspace-scoped engineering operations."""

    repository_root: Path | str


@dataclass(frozen=True, slots=True)
class ReadFileRequest(ToolRequest):
    path: str
    encoding: str = "utf-8"


@dataclass(frozen=True, slots=True)
class SearchFilesRequest(ToolRequest):
    query: str
    case_sensitive: bool = False
    regex: bool = False
    include_patterns: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()
    max_results: int = DEFAULT_MAX_SEARCH_RESULTS
    encoding: str = "utf-8"


@dataclass(frozen=True, slots=True)
class WriteFileRequest(ToolRequest):
    path: str
    content: str
    overwrite: bool = False
    create_parents: bool = False
    encoding: str = "utf-8"


@dataclass(frozen=True, slots=True)
class RunCommandRequest(ToolRequest):
    command: str
    arguments: tuple[str, ...] = ()
    timeout_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class _ResolvedRepositoryPath:
    root: Path
    path: Path
    relative_path: str


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _path_is_absolute(value: str) -> bool:
    windows_path = PureWindowsPath(value)
    posix_path = PurePosixPath(value)
    return (
        windows_path.is_absolute()
        or bool(windows_path.drive)
        or posix_path.is_absolute()
        or value.startswith(("/", "\\"))
    )


def _normalise_relative_path(value: object) -> tuple[tuple[str, ...] | None, ToolError | None]:
    if not isinstance(value, str) or not value.strip():
        return None, ToolError(
            "validation_error",
            "A non-empty relative path is required.",
        )
    if "\x00" in value:
        return None, ToolError(
            "validation_error",
            "The requested path contains a null byte.",
        )
    if _path_is_absolute(value):
        return None, ToolError(
            "path_violation",
            "Absolute paths are not allowed.",
        )

    raw_parts = value.replace("\\", "/").split("/")
    if any(part == ".." for part in raw_parts):
        return None, ToolError(
            "path_violation",
            "Path traversal outside the repository is not allowed.",
        )
    parts = tuple(part for part in raw_parts if part not in {"", "."})
    if not parts:
        return None, ToolError(
            "validation_error",
            "A file path is required.",
        )
    return parts, None


def _repository_root(value: object) -> tuple[Path | None, ToolError | None]:
    if not isinstance(value, (str, Path)):
        return None, ToolError(
            "validation_error",
            "A repository root path is required.",
        )
    try:
        root = Path(value).resolve(strict=True)
    except FileNotFoundError:
        return None, ToolError(
            "repository_not_found",
            "The repository root does not exist.",
        )
    except (OSError, RuntimeError, ValueError):
        return None, ToolError(
            "validation_error",
            "The repository root could not be resolved.",
        )

    try:
        if not root.is_dir():
            return None, ToolError(
                "validation_error",
                "The repository root must be a directory.",
            )
    except OSError:
        return None, ToolError(
            "permission_denied",
            "The repository root cannot be accessed.",
        )
    return root, None


def _resolve_repository_path(
    repository_root: object,
    relative_path: object,
) -> tuple[_ResolvedRepositoryPath | None, ToolError | None]:
    root, root_error = _repository_root(repository_root)
    if root_error:
        return None, root_error

    parts, path_error = _normalise_relative_path(relative_path)
    if path_error:
        return None, path_error

    assert root is not None
    assert parts is not None
    candidate = root.joinpath(*parts)
    current = root
    try:
        for part in parts:
            current = current / part
            if current.is_symlink():
                return None, ToolError(
                    "path_violation",
                    "Symlink paths are not allowed for repository file operations.",
                )
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None, ToolError(
            "path_violation",
            "The requested path could not be resolved safely.",
        )

    if not _is_within(resolved, root):
        return None, ToolError(
            "path_violation",
            "The requested path is outside the repository.",
        )

    return _ResolvedRepositoryPath(
        root=root,
        path=candidate,
        relative_path=PurePosixPath(*parts).as_posix(),
    ), None


def _encoding_error(encoding: object) -> ToolError | None:
    if not isinstance(encoding, str) or not encoding:
        return ToolError(
            "validation_error",
            "A non-empty text encoding is required.",
        )
    try:
        codecs.lookup(encoding)
    except LookupError:
        return ToolError(
            "validation_error",
            "The requested text encoding is not available.",
        )
    return None


RequestT = TypeVar("RequestT", bound=ToolRequest)


class EngineeringTool(ABC, Generic[RequestT]):
    """Base contract for one deterministic engineering operation."""

    name: ClassVar[str]
    description: ClassVar[str]
    request_type: ClassVar[type[ToolRequest]]
    result_type: ClassVar[type[ToolResult]] = ToolResult

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            description=self.description,
            input_model=self.request_type.__name__,
            output_model=self.result_type.__name__,
        )

    def _request_error(self, request: object) -> ToolResult | None:
        if not isinstance(request, self.request_type):
            return ToolResult.fail(
                self.name,
                "validation_error",
                f"{self.name} received an invalid request model.",
            )
        return None

    @abstractmethod
    def execute(self, request: RequestT) -> ToolResult:
        """Validate and execute exactly one operation."""


class ToolRegistry:
    """Deterministic registry used by a future orchestrator to discover tools."""

    def __init__(self) -> None:
        self._tools: dict[str, EngineeringTool[Any]] = {}

    def register(self, tool: EngineeringTool[Any]) -> None:
        if not isinstance(tool, EngineeringTool):
            raise TypeError("Only EngineeringTool instances can be registered.")
        if not isinstance(tool.name, str) or not tool.name:
            raise ValueError("Engineering tools require a stable non-empty name.")
        if tool.name in self._tools:
            raise ValueError(f"An engineering tool named {tool.name!r} is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> EngineeringTool[Any] | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolMetadata]:
        return [self._tools[name].metadata for name in sorted(self._tools)]

    def execute(self, name: str, request: ToolRequest) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            tool_name = name if isinstance(name, str) and len(name) <= 128 else "unknown"
            return ToolResult.fail(
                tool_name,
                "unknown_tool",
                "The requested engineering tool is not registered.",
            )
        return tool.execute(request)


class ReadFileTool(EngineeringTool[ReadFileRequest]):
    """Read one bounded UTF-8 (or explicitly selected encoding) text file."""

    name = "read_file"
    description = "Read one bounded text file from the repository."
    request_type = ReadFileRequest

    def __init__(self, limits: ToolLimits | None = None) -> None:
        self.limits = limits or ToolLimits()

    def execute(self, request: ReadFileRequest) -> ToolResult:
        request_error = self._request_error(request)
        if request_error:
            return request_error
        encoding_error = _encoding_error(request.encoding)
        if encoding_error:
            return ToolResult.fail(
                self.name,
                encoding_error.code,
                encoding_error.message,
                details=encoding_error.details,
            )
        resolved, path_error = _resolve_repository_path(
            request.repository_root,
            request.path,
        )
        if path_error:
            return ToolResult.fail(
                self.name,
                path_error.code,
                path_error.message,
                details=path_error.details,
            )
        assert resolved is not None

        try:
            if not resolved.path.exists():
                return ToolResult.fail(
                    self.name,
                    "file_not_found",
                    "The requested file does not exist.",
                    data={"path": resolved.relative_path},
                )
            if not resolved.path.is_file():
                return ToolResult.fail(
                    self.name,
                    "not_a_file",
                    "The requested path is not a regular file.",
                    data={"path": resolved.relative_path},
                )
            size_bytes = resolved.path.stat().st_size
        except PermissionError:
            return ToolResult.fail(
                self.name,
                "permission_denied",
                "The requested file cannot be read.",
                data={"path": resolved.relative_path},
            )
        except OSError:
            return ToolResult.fail(
                self.name,
                "io_error",
                "The requested file could not be inspected.",
                data={"path": resolved.relative_path},
            )

        if size_bytes > self.limits.max_read_bytes:
            return ToolResult.fail(
                self.name,
                "size_limit_exceeded",
                "The requested file exceeds the read size limit.",
                data={
                    "path": resolved.relative_path,
                    "size_bytes": size_bytes,
                    "max_bytes": self.limits.max_read_bytes,
                },
            )

        try:
            with resolved.path.open("rb") as source:
                raw_content = source.read(self.limits.max_read_bytes + 1)
        except PermissionError:
            return ToolResult.fail(
                self.name,
                "permission_denied",
                "The requested file cannot be read.",
                data={"path": resolved.relative_path},
            )
        except OSError:
            return ToolResult.fail(
                self.name,
                "io_error",
                "The requested file could not be read.",
                data={"path": resolved.relative_path},
            )

        if len(raw_content) > self.limits.max_read_bytes:
            return ToolResult.fail(
                self.name,
                "size_limit_exceeded",
                "The requested file exceeds the read size limit.",
                data={
                    "path": resolved.relative_path,
                    "max_bytes": self.limits.max_read_bytes,
                },
            )

        try:
            content = raw_content.decode(request.encoding)
        except UnicodeDecodeError:
            return ToolResult.fail(
                self.name,
                "decode_error",
                "The requested file could not be decoded with the selected encoding.",
                data={"path": resolved.relative_path},
            )

        return ToolResult.ok(
            self.name,
            {
                "path": resolved.relative_path,
                "content": content,
                "size_bytes": len(raw_content),
                "encoding": request.encoding,
            },
        )


def _unsafe_filter_pattern(pattern: str) -> bool:
    if "\x00" in pattern or _path_is_absolute(pattern):
        return True
    return any(part == ".." for part in pattern.replace("\\", "/").split("/"))


def _validate_patterns(
    value: object,
    field_name: str,
) -> tuple[tuple[str, ...] | None, ToolError | None]:
    if not isinstance(value, (tuple, list)):
        return None, ToolError(
            "validation_error",
            f"{field_name} must be a sequence of relative glob patterns.",
        )
    patterns = []
    for pattern in value:
        if (
            not isinstance(pattern, str)
            or not pattern
            or len(pattern) > MAX_FILTER_CHARS
            or _unsafe_filter_pattern(pattern)
        ):
            return None, ToolError(
                "validation_error",
                f"{field_name} contains an invalid relative glob pattern.",
            )
        patterns.append(pattern.replace("\\", "/"))
    return tuple(patterns), None


def _regex_safety_error(pattern: str) -> ToolError | None:
    """Reject regex features with obvious catastrophic-backtracking potential."""

    if re.search(r"\\[1-9]", pattern):
        return ToolError(
            "validation_error",
            "Regex backreferences are not supported for bounded search.",
        )
    if re.search(r"\(\?(?:[=!]|<[=!])", pattern):
        return ToolError(
            "validation_error",
            "Regex lookaround is not supported for bounded search.",
        )
    if re.search(r"\((?:[^()\\]|\\.)*[*+](?:[^()\\]|\\.)*\)\s*[*+{]", pattern):
        return ToolError(
            "validation_error",
            "Nested regex quantifiers are not supported for bounded search.",
        )
    return None


def _truncate_snippet(line: str, maximum: int) -> tuple[str, bool]:
    if len(line) <= maximum:
        return line, False
    return line[:maximum], True


class SearchFilesTool(EngineeringTool[SearchFilesRequest]):
    """Search bounded text files that the repository scanner considers visible."""

    name = "search_files"
    description = "Search bounded repository text files for a literal or safe regex."
    request_type = SearchFilesRequest

    def __init__(self, limits: ToolLimits | None = None) -> None:
        self.limits = limits or ToolLimits()

    def execute(self, request: SearchFilesRequest) -> ToolResult:
        request_error = self._request_error(request)
        if request_error:
            return request_error
        if (
            not isinstance(request.query, str)
            or not request.query
            or len(request.query) > MAX_QUERY_CHARS
        ):
            return ToolResult.fail(
                self.name,
                "validation_error",
                "The search query must be non-empty and within the query limit.",
            )
        if (
            isinstance(request.max_results, bool)
            or not isinstance(request.max_results, int)
            or request.max_results <= 0
            or request.max_results > self.limits.max_search_results
        ):
            return ToolResult.fail(
                self.name,
                "validation_error",
                "max_results must be a positive value within the configured limit.",
                details={"max_results_limit": self.limits.max_search_results},
            )
        encoding_error = _encoding_error(request.encoding)
        if encoding_error:
            return ToolResult.fail(
                self.name,
                encoding_error.code,
                encoding_error.message,
                details=encoding_error.details,
            )
        include_patterns, include_error = _validate_patterns(
            request.include_patterns,
            "include_patterns",
        )
        if include_error:
            return ToolResult.fail(
                self.name,
                include_error.code,
                include_error.message,
            )
        exclude_patterns, exclude_error = _validate_patterns(
            request.exclude_patterns,
            "exclude_patterns",
        )
        if exclude_error:
            return ToolResult.fail(
                self.name,
                exclude_error.code,
                exclude_error.message,
            )
        root, root_error = _repository_root(request.repository_root)
        if root_error:
            return ToolResult.fail(
                self.name,
                root_error.code,
                root_error.message,
                details=root_error.details,
            )
        assert root is not None
        assert include_patterns is not None
        assert exclude_patterns is not None

        flags = 0 if request.case_sensitive else re.IGNORECASE
        if request.regex:
            safety_error = _regex_safety_error(request.query)
            if safety_error:
                return ToolResult.fail(
                    self.name,
                    safety_error.code,
                    safety_error.message,
                )
            try:
                matcher = re.compile(request.query, flags)
            except re.error:
                return ToolResult.fail(
                    self.name,
                    "validation_error",
                    "The supplied regex pattern is invalid.",
                )
        else:
            matcher = re.compile(re.escape(request.query), flags)

        matches: list[dict[str, Any]] = []
        skipped = {"binary": 0, "oversized": 0, "unreadable": 0}
        files_scanned = 0

        for discovered_path in RepositoryService(root).get_files():
            try:
                relative_path = discovered_path.relative_to(root).as_posix()
            except ValueError:
                continue
            if include_patterns and not any(
                fnmatch.fnmatchcase(relative_path, pattern)
                for pattern in include_patterns
            ):
                continue
            if any(
                fnmatch.fnmatchcase(relative_path, pattern)
                for pattern in exclude_patterns
            ):
                continue

            resolved, path_error = _resolve_repository_path(root, relative_path)
            if path_error or resolved is None:
                skipped["unreadable"] += 1
                continue
            try:
                size_bytes = resolved.path.stat().st_size
                if size_bytes > self.limits.max_search_file_bytes:
                    skipped["oversized"] += 1
                    continue
                with resolved.path.open("rb") as source:
                    raw_content = source.read(self.limits.max_search_file_bytes + 1)
            except (OSError, PermissionError):
                skipped["unreadable"] += 1
                continue

            if len(raw_content) > self.limits.max_search_file_bytes:
                skipped["oversized"] += 1
                continue
            if b"\x00" in raw_content:
                skipped["binary"] += 1
                continue
            try:
                content = raw_content.decode(request.encoding)
            except UnicodeDecodeError:
                skipped["binary"] += 1
                continue

            files_scanned += 1
            for line_number, line in enumerate(content.splitlines(), start=1):
                for match in matcher.finditer(line):
                    snippet, snippet_truncated = _truncate_snippet(
                        line,
                        self.limits.max_snippet_chars,
                    )
                    matches.append(
                        {
                            "path": relative_path,
                            "line": line_number,
                            "column": match.start() + 1,
                            "snippet": snippet,
                            "snippet_truncated": snippet_truncated,
                        }
                    )
                    if len(matches) >= request.max_results:
                        return ToolResult.ok(
                            self.name,
                            {
                                "matches": matches,
                                "match_count": len(matches),
                                "files_scanned": files_scanned,
                                "skipped": skipped,
                                "result_limit_reached": True,
                            },
                            metadata={"max_results": request.max_results},
                        )

        return ToolResult.ok(
            self.name,
            {
                "matches": matches,
                "match_count": len(matches),
                "files_scanned": files_scanned,
                "skipped": skipped,
                "result_limit_reached": False,
            },
            metadata={"max_results": request.max_results},
        )


class WriteFileTool(EngineeringTool[WriteFileRequest]):
    """Atomically create or replace one bounded repository text file."""

    name = "write_file"
    description = "Atomically write one bounded text file in the repository."
    request_type = WriteFileRequest

    def __init__(self, limits: ToolLimits | None = None) -> None:
        self.limits = limits or ToolLimits()

    def execute(self, request: WriteFileRequest) -> ToolResult:
        request_error = self._request_error(request)
        if request_error:
            return request_error
        if not isinstance(request.content, str):
            return ToolResult.fail(
                self.name,
                "validation_error",
                "File content must be text.",
            )
        encoding_error = _encoding_error(request.encoding)
        if encoding_error:
            return ToolResult.fail(
                self.name,
                encoding_error.code,
                encoding_error.message,
            )

        # Validate path BEFORE attempting to encode/size-check content (security priority)
        resolved, path_error = _resolve_repository_path(
            request.repository_root,
            request.path,
        )
        if path_error:
            return ToolResult.fail(
                self.name,
                path_error.code,
                path_error.message,
                details=path_error.details,
            )
        assert resolved is not None

        try:
            encoded_content = request.content.encode(request.encoding)
        except UnicodeEncodeError:
            return ToolResult.fail(
                self.name,
                "encode_error",
                "The supplied content cannot be encoded with the selected encoding.",
            )
        if len(encoded_content) > self.limits.max_write_bytes:
            return ToolResult.fail(
                self.name,
                "size_limit_exceeded",
                "The supplied content exceeds the write size limit.",
                details={"max_bytes": self.limits.max_write_bytes},
            )
        try:
            parent_exists = resolved.path.parent.exists()
            if parent_exists and not resolved.path.parent.is_dir():
                return ToolResult.fail(
                    self.name,
                    "parent_not_directory",
                    "The requested file parent is not a directory.",
                    data={"path": resolved.relative_path},
                )
            if not parent_exists:
                if not request.create_parents:
                    return ToolResult.fail(
                        self.name,
                        "parent_not_found",
                        "The requested file parent does not exist.",
                        data={"path": resolved.relative_path},
                    )
                resolved.path.parent.mkdir(parents=True, exist_ok=True)
                resolved, path_error = _resolve_repository_path(
                    request.repository_root,
                    request.path,
                )
                if path_error:
                    return ToolResult.fail(
                        self.name,
                        path_error.code,
                        path_error.message,
                        details=path_error.details,
                    )
                assert resolved is not None

            target_exists = resolved.path.exists()
            if target_exists and not resolved.path.is_file():
                return ToolResult.fail(
                    self.name,
                    "not_a_file",
                    "The requested path is not a regular file.",
                    data={"path": resolved.relative_path},
                )
            if target_exists and not request.overwrite:
                return ToolResult.fail(
                    self.name,
                    "file_exists",
                    "The requested file already exists and overwrite is disabled.",
                    data={"path": resolved.relative_path},
                )
        except PermissionError:
            return ToolResult.fail(
                self.name,
                "permission_denied",
                "The requested file location cannot be written.",
                data={"path": resolved.relative_path},
            )
        except OSError:
            return ToolResult.fail(
                self.name,
                "io_error",
                "The requested file location could not be prepared.",
                data={"path": resolved.relative_path},
            )

        temporary_path: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".forge-",
                suffix=".tmp",
                dir=resolved.path.parent,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(encoded_content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, resolved.path)
        except PermissionError:
            return ToolResult.fail(
                self.name,
                "permission_denied",
                "The requested file could not be written.",
                data={"path": resolved.relative_path},
            )
        except OSError:
            return ToolResult.fail(
                self.name,
                "io_error",
                "The requested file could not be written atomically.",
                data={"path": resolved.relative_path},
            )
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

        return ToolResult.ok(
            self.name,
            {
                "path": resolved.relative_path,
                "size_bytes": len(encoded_content),
                "created": not target_exists,
                "overwritten": target_exists,
                "encoding": request.encoding,
            },
        )


def _contains_parent_reference(value: str) -> bool:
    return any(part == ".." for part in value.replace("\\", "/").split("/"))


def _unsafe_command_path_argument(argument: str) -> bool:
    """Reject explicit argument paths that would target outside the workspace."""

    candidates = [argument]
    if "=" in argument:
        candidates.append(argument.split("=", 1)[1])
    if argument.startswith("@"):
        candidates.append(argument[1:])

    return any(
        _path_is_absolute(candidate) or _contains_parent_reference(candidate)
        for candidate in candidates
        if candidate
    )


def _is_python_interpreter(command: str) -> bool:
    executable_name = Path(command).name.lower()
    return bool(re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", executable_name))


def _redacted_arguments(arguments: tuple[str, ...]) -> list[str]:
    """Preserve command diagnostics without echoing common secret arguments."""

    sensitive = re.compile(
        r"(?:token|password|secret|api[_-]?key|credential)",
        re.IGNORECASE,
    )
    display: list[str] = []
    redact_next = False
    for argument in arguments:
        if redact_next:
            display.append("<redacted>")
            redact_next = False
            continue
        option, separator, value = argument.partition("=")
        if sensitive.search(option):
            display.append(f"{option}=<redacted>" if separator else option)
            redact_next = not bool(separator)
        else:
            display.append(argument)
    return display


@dataclass(slots=True)
class _CapturedStream:
    content: bytearray = field(default_factory=bytearray)
    truncated: bool = False


def _drain_stream(
    stream: Any,
    maximum_bytes: int,
    captured: _CapturedStream,
) -> None:
    """Drain a subprocess pipe while retaining only a bounded prefix."""

    try:
        while True:
            chunk = stream.read(8_192)
            if not chunk:
                return
            remaining = maximum_bytes - len(captured.content)
            if remaining > 0:
                captured.content.extend(chunk[:remaining])
            if len(chunk) > remaining:
                captured.truncated = True
    finally:
        try:
            stream.close()
        except OSError:
            pass


class RunCommandTool(EngineeringTool[RunCommandRequest]):
    """Execute one explicit command in the repository without a shell."""

    name = "run_command"
    description = "Run one bounded, timed developer command in the repository."
    request_type = RunCommandRequest

    def __init__(self, limits: ToolLimits | None = None) -> None:
        self.limits = limits or ToolLimits()

    def execute(self, request: RunCommandRequest) -> ToolResult:
        request_error = self._request_error(request)
        if request_error:
            return request_error
        root, root_error = _repository_root(request.repository_root)
        if root_error:
            return ToolResult.fail(
                self.name,
                root_error.code,
                root_error.message,
                details=root_error.details,
            )
        assert root is not None

        if (
            not isinstance(request.command, str)
            or not request.command.strip()
            or len(request.command) > MAX_COMMAND_CHARS
            or "\x00" in request.command
            or _contains_parent_reference(request.command)
        ):
            return ToolResult.fail(
                self.name,
                "validation_error",
                "The command must be a bounded executable name or path.",
            )
        if not isinstance(request.arguments, (tuple, list)):
            return ToolResult.fail(
                self.name,
                "validation_error",
                "Command arguments must be a sequence of strings.",
            )
        if len(request.arguments) > MAX_COMMAND_ARGUMENTS:
            return ToolResult.fail(
                self.name,
                "validation_error",
                "The command exceeds the maximum number of arguments.",
            )
        arguments: tuple[str, ...] = tuple(request.arguments)
        for argument in arguments:
            if (
                not isinstance(argument, str)
                or len(argument) > MAX_COMMAND_ARGUMENT_CHARS
                or "\x00" in argument
                or _unsafe_command_path_argument(argument)
            ):
                return ToolResult.fail(
                    self.name,
                    "validation_error",
                    "Command arguments contain an invalid path or value.",
                )
        if _is_python_interpreter(request.command) and (
            "-c" in arguments or "-" in arguments
        ):
            return ToolResult.fail(
                self.name,
                "validation_error",
                "Direct Python source execution is not supported.",
            )

        timeout_seconds = (
            self.limits.default_command_timeout_seconds
            if request.timeout_seconds is None
            else request.timeout_seconds
        )
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or timeout_seconds > self.limits.max_command_timeout_seconds
        ):
            return ToolResult.fail(
                self.name,
                "validation_error",
                "timeout_seconds must be positive and within the configured limit.",
                details={
                    "max_timeout_seconds": self.limits.max_command_timeout_seconds
                },
            )

        started_at = time.monotonic()
        try:
            process = subprocess.Popen(
                [request.command, *arguments],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                start_new_session=True,
            )
        except FileNotFoundError:
            return ToolResult.fail(
                self.name,
                "command_not_found",
                "The requested command could not be started.",
            )
        except PermissionError:
            return ToolResult.fail(
                self.name,
                "permission_denied",
                "The requested command cannot be executed.",
            )
        except OSError:
            return ToolResult.fail(
                self.name,
                "execution_error",
                "The requested command could not be started.",
            )

        assert process.stdout is not None
        assert process.stderr is not None
        captured_stdout = _CapturedStream()
        captured_stderr = _CapturedStream()
        stdout_thread = threading.Thread(
            target=_drain_stream,
            args=(
                process.stdout,
                self.limits.max_command_output_bytes,
                captured_stdout,
            ),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_drain_stream,
            args=(
                process.stderr,
                self.limits.max_command_output_bytes,
                captured_stderr,
            ),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        timed_out = False
        try:
            exit_code = process.wait(timeout=float(timeout_seconds))
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                exit_code = process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                exit_code = process.wait(timeout=2)
        finally:
            stdout_thread.join()
            stderr_thread.join()

        duration_seconds = time.monotonic() - started_at
        result_data = {
            "command": request.command,
            "arguments": _redacted_arguments(arguments),
            "exit_code": exit_code,
            "stdout": captured_stdout.content.decode("utf-8", errors="replace"),
            "stderr": captured_stderr.content.decode("utf-8", errors="replace"),
            "stdout_truncated": captured_stdout.truncated,
            "stderr_truncated": captured_stderr.truncated,
            "timed_out": timed_out,
            "duration_seconds": duration_seconds,
        }
        if timed_out:
            return ToolResult.fail(
                self.name,
                "timeout",
                "The command exceeded its timeout.",
                data=result_data,
                details={"timeout_seconds": float(timeout_seconds)},
            )
        if exit_code != 0:
            return ToolResult.fail(
                self.name,
                "command_failed",
                "The command exited with a non-zero status.",
                data=result_data,
                details={"exit_code": exit_code},
            )
        return ToolResult.ok(self.name, result_data)


def create_default_tool_registry(
    limits: ToolLimits | None = None,
) -> ToolRegistry:
    """Create the Phase 4 registry with the four supported operations."""

    shared_limits = limits or ToolLimits()
    registry = ToolRegistry()
    registry.register(ReadFileTool(shared_limits))
    registry.register(SearchFilesTool(shared_limits))
    registry.register(WriteFileTool(shared_limits))
    registry.register(RunCommandTool(shared_limits))
    return registry
