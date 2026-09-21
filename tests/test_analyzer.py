from pathlib import Path

import pytest

from app.services.analyzer import RepositoryAnalyzer
from app.services.repository import RepositoryService


def test_analyze_counts_file_types(tmp_path: Path):
    (tmp_path / "app").mkdir()
    (tmp_path / "tests").mkdir()

    (tmp_path / "app" / "main.py").write_text("")
    (tmp_path / "app" / "app.py").write_text("")
    (tmp_path / "app" / "script.js").write_text("")
    (tmp_path / "app" / "types.ts").write_text("")
    (tmp_path / "tests" / "test_main.py").write_text("")
    (tmp_path / "pyproject.toml").write_text("")

    (tmp_path / "app" / "api_example.py").write_text(
        "from fastapi import FastAPI\n\napp = FastAPI()"
    )

    (tmp_path / "app" / "django_example.py").write_text(
        "from django.http import HttpResponse\n"
    )

    (tmp_path / "app" / "flask_example.py").write_text(
        "from flask import Flask\n"
    )

    (tmp_path / "app" / "react_example.ts").write_text(
        "import React from 'react'\n"
    )

    (tmp_path / "app" / "next_example.ts").write_text(
        "import Link from 'next/link'\n"
    )

    (tmp_path / "app" / "express_example.js").write_text(
        "import express from 'express'\n"
    )

    repository = RepositoryService(root_path=tmp_path)
    analyzer = RepositoryAnalyzer(repository)

    result = analyzer.analyze()

    assert result["summary"]["total_files"] == 12
    assert result["summary"]["python_files"] == 6
    assert result["summary"]["javascript_files"] == 2
    assert result["summary"]["typescript_files"] == 3
    assert result["summary"]["test_files"] == 1
    assert result["summary"]["other_files"] == 1

    assert result["project_type"] == "python"
    assert result["has_tests"] is True
    assert result["directories"] == ["app", "tests"]
    assert result["metadata_files"] == ["pyproject.toml"]

    assert result["technologies"] == [
        "Django",
        "Express",
        "FastAPI",
        "Flask",
        "Next.js",
        "Python",
        "React",
    ]

    assert result["frameworks"] == [
        "Django",
        "Express",
        "FastAPI",
        "Flask",
        "Next.js",
        "React",
    ]

    assert result["dependencies"] == []
    assert result["lockfiles"] == []
    assert result["entry_points"] == ["app/main.py"]


def test_analyze_detects_python_entry_points(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('main')")
    (tmp_path / "cli.py").write_text(
        "if __name__ == '__main__':\n    print('cli')\n"
    )

    (tmp_path / "package").mkdir()
    (tmp_path / "package" / "__main__.py").write_text("print('package')")

    (tmp_path / "not_entry.py").write_text(
        "message = \"if __name__ == '__main__':\"\n"
        "# if __name__ == '__main__':\n"
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["entry_points"] == [
        "cli.py",
        "main.py",
        "package/__main__.py",
    ]


def test_analyze_detects_existing_package_entry_points(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "bin").mkdir()

    (tmp_path / "src" / "index.js").write_text("")
    (tmp_path / "src" / "module.js").write_text("")
    (tmp_path / "bin" / "cli.js").write_text("")
    (tmp_path / "feature.js").write_text("")

    (tmp_path / "package.json").write_text(
        "{"
        '"main": "src/index.js", '
        '"module": "src/index.js", '
        '"bin": {"forge": "bin/cli.js"}, '
        '"exports": {".": {"import": "src/module.js"}, '
        '"./feature": "feature.js"}'
        "}"
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["entry_points"] == [
        "bin/cli.js",
        "feature.js",
        "src/index.js",
        "src/module.js",
    ]


def test_analyze_normalizes_windows_package_entry_point_paths(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.js").write_text("")

    (tmp_path / "package.json").write_text(
        r'{"main": "src\\\\main.js"}'
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["entry_points"] == ["src/main.js"]


def test_analyze_ignores_nonexistent_and_malformed_package_entry_points(
    tmp_path: Path,
):
    (tmp_path / "real.js").write_text("")

    (tmp_path / "package.json").write_text(
        '{"main": "real.js", "module": "missing.js", '
        '"bin": {"tool": "missing-cli.js"}, '
        '"exports": {".": "missing-export.js"}}'
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["entry_points"] == ["real.js"]

    (tmp_path / "package.json").write_text("not json")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["entry_points"] == []


def test_analyze_reports_no_entry_points(tmp_path: Path):
    (tmp_path / "README.md").write_text("No executable entry point here")
    (tmp_path / "utility.py").write_text(
        "def helper():\n    return True\n"
    )
    (tmp_path / "package.json").write_text('{"name": "library"}')

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["entry_points"] == []


def test_analyze_detects_dependencies_and_lockfiles(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text(
        "fastapi>=0.100\n"
        "requests[security]==2.0\n"
        "# ignored-package\n"
        "-r base.txt\n"
        "git+https://example.com/lib.git#egg=editable-lib\n"
    )

    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        "dependencies = ['pydantic>=2', 'httpx']\n"
        "[project.optional-dependencies]\n"
        "dev = ['pytest']\n"
    )

    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react": "^18"}, '
        '"devDependencies": {"typescript": "^5"}, '
        '"peerDependencies": {"next": "^14"}}'
    )

    (tmp_path / "package-lock.json").write_text("{}")
    (tmp_path / "poetry.lock").write_text("not parsed yet")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["dependencies"] == [
        "editable-lib",
        "fastapi",
        "httpx",
        "next",
        "pydantic",
        "pytest",
        "react",
        "requests",
        "typescript",
    ]

    assert result["lockfiles"] == [
        "package-lock.json",
        "poetry.lock",
    ]

    assert result["frameworks"] == []
    assert result["technologies"] == [
        "JavaScript/Node.js",
        "Python",
    ]


def test_analyze_ignores_invalid_dependency_manifests(tmp_path: Path):
    (tmp_path / "requirements.txt").write_bytes(b"\xff\xfe")
    (tmp_path / "pyproject.toml").write_text("[invalid")
    (tmp_path / "package.json").write_text("not json")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["dependencies"] == []
    assert result["lockfiles"] == []


@pytest.mark.parametrize(
    ("content", "suffix", "framework"),
    [
        ("from fastapi import FastAPI", ".py", "FastAPI"),
        ("import fastapi as api", ".py", "FastAPI"),
        ("from django.http import HttpResponse", ".py", "Django"),
        ("import django", ".py", "Django"),
        ("from flask import Flask", ".py", "Flask"),
        ("import flask", ".py", "Flask"),
        ('import React from "react"', ".js", "React"),
        ('import { useState } from "react"', ".ts", "React"),
        ('import express from "express"', ".js", "Express"),
        ('const express = require("express")', ".js", "Express"),
        ('import Link from "next/link"', ".ts", "Next.js"),
        ('const next = require("next")', ".js", "Next.js"),
    ],
)
def test_detect_frameworks_supports_real_imports(
    content: str,
    suffix: str,
    framework: str,
):
    analyzer = RepositoryAnalyzer(repository=None)

    assert analyzer._detect_frameworks(content, suffix) == {framework}


@pytest.mark.parametrize(
    ("content", "suffix"),
    [
        ("# from flask import Flask", ".py"),
        ('text = "import django"', ".py"),
        ('message = "from fastapi import FastAPI"', ".py"),
        ('// import React from "react"', ".js"),
        ('const text = "express"', ".js"),
        ('const text = "next/router"', ".ts"),
        ('const text = "require"; ("express")', ".js"),
        ("import fastapi as api", ".js"),
        ('import React from "react"', ".py"),
    ],
)
def test_detect_frameworks_ignores_non_import_text_and_wrong_file_types(
    content: str,
    suffix: str,
):
    analyzer = RepositoryAnalyzer(repository=None)

    assert analyzer._detect_frameworks(content, suffix) == set()


def test_detects_configuration_files(tmp_path: Path):
    config_files = [
        ".env.example",
        ".env.template",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "tsconfig.json",
        "vite.config.js",
        "vite.config.ts",
        "webpack.config.js",
        "webpack.config.ts",
        "pytest.ini",
        "tox.ini",
        "ruff.toml",
        ".mypy.ini",
    ]

    for filename in config_files:
        (tmp_path / filename).write_text("", encoding="utf-8")

    repository = RepositoryService(tmp_path)
    analyzer = RepositoryAnalyzer(repository)
    result = analyzer.analyze()

    assert result["configurations"] == sorted(config_files)


def test_detects_configuration_files_in_subdirectories(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "pytest.ini").write_text("", encoding="utf-8")
    (config_dir / "vite.config.ts").write_text("", encoding="utf-8")

    repository = RepositoryService(tmp_path)
    analyzer = RepositoryAnalyzer(repository)
    result = analyzer.analyze()

    assert result["configurations"] == [
        "config/pytest.ini",
        "config/vite.config.ts",
    ]


def test_does_not_detect_non_configuration_files(tmp_path: Path):
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )
    (tmp_path / "settings.txt").write_text(
        "",
        encoding="utf-8",
    )
    (tmp_path / "config.json").write_text(
        "{}",
        encoding="utf-8",
    )

    repository = RepositoryService(tmp_path)
    analyzer = RepositoryAnalyzer(repository)
    result = analyzer.analyze()

    assert result["configurations"] == []