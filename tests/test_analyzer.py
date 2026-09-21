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
    assert result["architecture"]["style"] == "unknown"


def test_analyze_detects_forge_layered_backend_structure(tmp_path: Path):
    (tmp_path / "app" / "api").mkdir(parents=True)
    (tmp_path / "app" / "services").mkdir(parents=True)
    (tmp_path / "tests").mkdir()

    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "api" / "routes.py").write_text(
        "from fastapi import APIRouter\n\nrouter = APIRouter()\n"
    )
    (tmp_path / "app" / "services" / "repository.py").write_text(
        "class Repository:\n    def get(self):\n        return None\n"
    )
    (tmp_path / "app" / "services" / "analyzer.py").write_text(
        "class Analyzer:\n    def analyze(self):\n        return {}\n"
    )
    (tmp_path / "app" / "main.py").write_text(
        "from app.api.routes import router\n"
    )
    (tmp_path / "tests" / "test_routes.py").write_text("")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["architecture"]["style"] == "layered"
    assert result["architecture"]["layers"] == [
        "api",
        "repository",
        "services",
        "tests",
    ]
    assert result["architecture"]["components"] == [
        "backend",
        "python_package",
    ]
    assert result["architecture"]["evidence"]


def test_analyze_detects_frontend_backend_separation(tmp_path: Path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "backend" / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n"
    )
    (tmp_path / "frontend" / "app.ts").write_text(
        "export const app = {};\n"
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["architecture"]["style"] == "frontend-backend"
    assert result["architecture"]["components"] == [
        "backend",
        "frontend",
    ]


def test_analyze_detects_test_and_configuration_layers(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_app(): pass\n")
    (tmp_path / "pytest.ini").write_text("[pytest]\n")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["architecture"]["style"] == "unknown"
    assert result["architecture"]["layers"] == [
        "configuration",
        "tests",
    ]


def test_analyze_reports_unknown_architecture_for_minimal_repository(tmp_path: Path):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "notes.txt").write_text("not source code")
    (tmp_path / "README.md").write_text("Minimal repository\n")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["architecture"] == {
        "style": "unknown",
        "layers": [],
        "components": [],
        "evidence": [],
    }


def test_analyze_architecture_is_deterministic(tmp_path: Path):
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "service.py").write_text(
        "class Service:\n    pass\n"
    )

    analyzer = RepositoryAnalyzer(RepositoryService(tmp_path))

    assert analyzer.analyze()["architecture"] == analyzer.analyze()["architecture"]


def test_analyze_builds_repository_index_for_multiple_file_types(tmp_path: Path):
    (tmp_path / "src" / "nested").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "nested" / "module.py").write_text(
        "import json\n\nVALUE = 1\n"
    )
    (tmp_path / "src" / "app.js").write_text("const app = {};\n")
    (tmp_path / "tests" / "test_module.py").write_text(
        "def test_module():\n    pass\n"
    )
    (tmp_path / "README.md").write_text("# Example\n")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()
    records = result["index"]["files"]

    assert [record["path"] for record in records] == [
        "README.md",
        "src/app.js",
        "src/nested/module.py",
        "tests/test_module.py",
    ]
    assert result["index"]["total_files"] == 4
    assert records[0]["file_type"] == "metadata"
    assert records[1]["language"] == "javascript"
    assert records[2]["imports"] == ["json"]
    assert records[2]["structure"]["constants"] == [
        {"name": "VALUE", "line": 3}
    ]
    assert records[3]["is_test"] is True


def test_analyze_index_excludes_ignored_directories(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "Git").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / ".pytest_cache").mkdir()

    for directory in [
        ".git",
        ".venv",
        "Git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
    ]:
        (tmp_path / directory / "ignored.py").write_text("import os\n")

    (tmp_path / "kept.py").write_text("import os\n")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert [record["path"] for record in result["index"]["files"]] == [
        "kept.py"
    ]


def test_analyze_index_handles_invalid_python(tmp_path: Path):
    (tmp_path / "broken.py").write_text("def broken(:\n    pass\n")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()
    record = result["index"]["files"][0]

    assert record["path"] == "broken.py"
    assert record["imports"] == []
    assert record["structure"] == {
        "classes": [],
        "functions": [],
        "methods": [],
        "constants": [],
        "global_assignments": [],
    }


def test_analyze_index_is_empty_for_empty_repository(tmp_path: Path):
    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["index"] == {
        "files": [],
        "total_files": 0,
    }


def test_analyze_index_order_is_deterministic(tmp_path: Path):
    (tmp_path / "z.py").write_text("")
    (tmp_path / "a.txt").write_text("text")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "m.py").write_text("")

    analyzer = RepositoryAnalyzer(RepositoryService(tmp_path))
    first = analyzer.analyze()["index"]
    second = analyzer.analyze()["index"]

    assert first == second
    assert [record["path"] for record in first["files"]] == [
        "a.txt",
        "nested/m.py",
        "z.py",
    ]


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


def test_analyze_code_structure_detects_definitions_and_decorators(
    tmp_path: Path,
):
    (tmp_path / "structure.py").write_text(
        "CONSTANT = 42\n"
        "value = 1\n"
        "@decorator\n"
        "def top_level(value):\n"
        "    return value\n"
        "\n"
        "async def fetch_data():\n"
        "    return None\n"
        "\n"
        "@dataclass\n"
        "class Service:\n"
        "    @staticmethod\n"
        "    def build():\n"
        "        return Service()\n"
        "\n"
        "    @classmethod\n"
        "    async def load(cls):\n"
        "        return cls()\n",
        encoding="utf-8",
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["code_structure"]["structure.py"] == {
        "classes": [
            {
                "name": "Service",
                "line": 11,
                "async": False,
                "decorators": ["dataclass"],
            }
        ],
        "functions": [
            {
                "name": "top_level",
                "line": 4,
                "async": False,
                "decorators": ["decorator"],
            },
            {
                "name": "fetch_data",
                "line": 7,
                "async": True,
                "decorators": [],
            },
        ],
        "methods": [
            {
                "name": "build",
                "line": 13,
                "async": False,
                "decorators": ["staticmethod"],
                "class": "Service",
            },
            {
                "name": "load",
                "line": 17,
                "async": True,
                "decorators": ["classmethod"],
                "class": "Service",
            },
        ],
        "constants": [{"name": "CONSTANT", "line": 1}],
        "global_assignments": [
            {"name": "CONSTANT", "line": 1},
            {"name": "value", "line": 2},
        ],
    }


def test_analyze_code_structure_supports_multiple_files(tmp_path: Path):
    (tmp_path / "first.py").write_text("class First:\n    pass\n")
    (tmp_path / "second.py").write_text(
        "def second():\n    return True\n"
    )

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert list(result["code_structure"]) == ["first.py", "second.py"]
    assert result["code_structure"]["first.py"]["classes"][0]["name"] == "First"
    assert result["code_structure"]["second.py"]["functions"][0]["name"] == "second"


def test_analyze_code_structure_handles_invalid_python(tmp_path: Path):
    (tmp_path / "broken.py").write_text("def broken(:\n    pass\n")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["code_structure"]["broken.py"] == {
        "classes": [],
        "functions": [],
        "methods": [],
        "constants": [],
        "global_assignments": [],
    }


def test_analyze_code_structure_handles_empty_python_file(tmp_path: Path):
    (tmp_path / "empty.py").write_text("")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["code_structure"] == {
        "empty.py": {
            "classes": [],
            "functions": [],
            "methods": [],
            "constants": [],
            "global_assignments": [],
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