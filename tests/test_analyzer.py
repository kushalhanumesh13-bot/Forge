from pathlib import Path
import subprocess

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
    assert result["imports"]["app/main.py"] == {
        "imports": [],
        "standard_library": [],
        "third_party": [],
        "local_project": [],
    }


def test_analyze_detects_python_import_categories(tmp_path: Path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text(
        "import json\n"
        "import os.path\n"
        "import requests\n"
        "import app.services.repository\n"
        "from pathlib import Path\n"
        "from requests import get\n"
        "from app import helper\n"
    )
    (tmp_path / "app" / "helper.py").write_text("VALUE = 1\n")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["imports"]["app/main.py"] == {
        "imports": [
            "app",
            "app.services.repository",
            "json",
            "os.path",
            "pathlib",
            "requests",
        ],
        "standard_library": ["json", "os.path", "pathlib"],
        "third_party": ["requests"],
        "local_project": ["app", "app.services.repository"],
    }


def test_analyze_handles_nested_and_invalid_python_imports(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "nested.py").write_text(
        "from pkg.submodule import value\n"
        "from . import sibling\n"
    )
    (tmp_path / "broken.py").write_text(
        "from valid import\n"
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["imports"]["pkg/nested.py"] == {
        "imports": [".", "pkg.submodule"],
        "standard_library": [],
        "third_party": [],
        "local_project": [".", "pkg.submodule"],
    }
    assert result["imports"]["broken.py"] == {
        "imports": [],
        "standard_library": [],
        "third_party": [],
        "local_project": [],
    }


def test_analyze_reports_empty_imports_for_python_files_without_imports(
    tmp_path: Path,
):
    (tmp_path / "plain.py").write_text(
        "# import os\n"
        "message = 'import requests'\n"
        "def helper():\n"
        "    return True\n"
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["imports"] == {
        "plain.py": {
            "imports": [],
            "standard_library": [],
            "third_party": [],
            "local_project": [],
        }
    }


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


def test_analyze_normalizes_windows_package_entry_point_paths(
    tmp_path: Path,
):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.js").write_text("")

    (tmp_path / "package.json").write_text(
        '{"main": "src\\\\main.js"}'
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
    (tmp_path / "README.md").write_text(
        "No executable entry point here"
    )

    (tmp_path / "utility.py").write_text(
        "def helper():\n    return True\n"
    )

    (tmp_path / "package.json").write_text(
        '{"name": "library"}'
    )

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
        (tmp_path / filename).write_text(
            "",
            encoding="utf-8",
        )

    repository = RepositoryService(tmp_path)
    analyzer = RepositoryAnalyzer(repository)
    result = analyzer.analyze()

    assert result["configurations"] == sorted(config_files)


def test_detects_configuration_files_in_subdirectories(
    tmp_path: Path,
):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "pytest.ini").write_text(
        "",
        encoding="utf-8",
    )

    (config_dir / "vite.config.ts").write_text(
        "",
        encoding="utf-8",
    )

    repository = RepositoryService(tmp_path)
    analyzer = RepositoryAnalyzer(repository)
    result = analyzer.analyze()

    assert result["configurations"] == [
        "config/pytest.ini",
        "config/vite.config.ts",
    ]


def test_does_not_detect_non_configuration_files(
    tmp_path: Path,
):
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


def test_analyze_readme(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "# Forge\n\n"
        "An AI-powered engineering workspace for developers.\n\n"
        "## Installation\n\n"
        "Install the project.\n\n"
        "## Usage\n\n"
        "Run Forge locally.\n\n"
        "### Configuration\n\n"
        "Configure the project.\n",
        encoding="utf-8",
    )

    result = RepositoryAnalyzer(
        RepositoryService(tmp_path)
    ).analyze()

    assert result["readme"] == {
        "present": True,
        "path": "README.md",
        "title": "Forge",
        "description": (
            "An AI-powered engineering workspace for developers."
        ),
        "sections": [
            "Installation",
            "Usage",
            "Configuration",
        ],
    }


def test_analyze_readme_in_subdirectory(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()

    (docs / "README.md").write_text(
        "# Documentation\n\n"
        "Project documentation.\n\n"
        "## Setup\n\n"
        "Setup instructions.\n",
        encoding="utf-8",
    )

    result = RepositoryAnalyzer(
        RepositoryService(tmp_path)
    ).analyze()

    assert result["readme"] == {
        "present": True,
        "path": "docs/README.md",
        "title": "Documentation",
        "description": "Project documentation.",
        "sections": ["Setup"],
    }


def test_analyze_without_readme(tmp_path: Path):
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    result = RepositoryAnalyzer(
        RepositoryService(tmp_path)
    ).analyze()

    assert result["readme"] == {
        "present": False,
        "path": None,
        "title": None,
        "description": None,
        "sections": [],
    }
def test_analyze_git_information(tmp_path: Path):
    repository = RepositoryService(tmp_path)

    def run_git(*arguments: str):
        return subprocess.run(
            ["git", *arguments],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

    run_git("init")
    run_git("config", "user.name", "Forge Test")
    run_git("config", "user.email", "forge-test@example.com")

    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    run_git("add", "main.py")
    run_git("commit", "-m", "initial commit")

    result = RepositoryAnalyzer(repository).analyze()

    assert result["git"]["is_repository"] is True
    assert result["git"]["branch"] in {"main", "master"}
    assert len(result["git"]["commit"]) == 40
    assert result["git"]["is_clean"] is True
    assert result["git"]["changed_files"] == []
    assert result["git"]["remote"] is None


def test_analyze_git_detects_changed_files(tmp_path: Path):
    repository = RepositoryService(tmp_path)

    def run_git(*arguments: str):
        return subprocess.run(
            ["git", *arguments],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

    run_git("init")
    run_git("config", "user.name", "Forge Test")
    run_git("config", "user.email", "forge-test@example.com")

    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    run_git("add", "main.py")
    run_git("commit", "-m", "initial commit")

    (tmp_path / "main.py").write_text(
        "print('changed')",
        encoding="utf-8",
    )

    (tmp_path / "new.py").write_text(
        "print('new')",
        encoding="utf-8",
    )

    result = RepositoryAnalyzer(repository).analyze()

    assert result["git"]["is_repository"] is True
    assert result["git"]["is_clean"] is False
    assert result["git"]["changed_files"] == [
        "main.py",
        "new.py",
    ]


def test_analyze_git_detects_remote(tmp_path: Path):
    repository = RepositoryService(tmp_path)

    def run_git(*arguments: str):
        return subprocess.run(
            ["git", *arguments],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )

    run_git("init")
    run_git("remote", "add", "origin", "https://github.com/example/forge.git")

    result = RepositoryAnalyzer(repository).analyze()

    assert result["git"]["is_repository"] is True
    assert result["git"]["remote"] == (
        "https://github.com/example/forge.git"
    )


def test_analyze_git_without_repository(tmp_path: Path):
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    result = RepositoryAnalyzer(
        RepositoryService(tmp_path)
    ).analyze()

    assert result["git"] == {
        "is_repository": False,
        "branch": None,
        "commit": None,
        "is_clean": None,
        "changed_files": [],
        "remote": None,
    }