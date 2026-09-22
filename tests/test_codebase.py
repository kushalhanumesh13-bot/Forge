from pathlib import Path

from app.services.analyzer import RepositoryAnalyzer
from app.services.repository import RepositoryService


def analyze(tmp_path: Path):
    return RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()


def test_codebase_modules_and_symbol_index_capture_python_facts(
    tmp_path: Path,
):
    (tmp_path / "module.py").write_text(
        "VALUE = 1\n"
        "_internal = 2\n"
        "@decorate\n"
        "def public_function():\n"
        "    return VALUE\n"
        "\n"
        "async def fetch():\n"
        "    return None\n"
        "\n"
        "@dataclass\n"
        "class PublicClass:\n"
        "    @staticmethod\n"
        "    def build():\n"
        "        return PublicClass()\n"
        "\n"
        "    async def _load(self):\n"
        "        return self.build()\n",
        encoding="utf-8",
    )

    understanding = analyze(tmp_path)["codebase_understanding"]

    module = understanding["modules"][0]

    assert module["path"] == "module.py"
    assert module["module"] == "module"
    assert module["parse_status"] == "parsed"
    assert module["public_symbols"] == [
        "PublicClass",
        "VALUE",
        "fetch",
        "public_function",
    ]
    assert module["private_symbols"] == ["_internal"]
    assert module["constants"] == [{"name": "VALUE", "line": 1}]
    assert [symbol["name"] for symbol in module["async_functions"]] == [
        "fetch",
        "_load",
    ]

    symbols = understanding["symbols"]
    assert symbols == [
        {
            "name": "public_function",
            "type": "function",
            "file": "module.py",
            "line": 4,
            "end_line": 5,
            "parent": None,
            "decorators": ["decorate"],
            "visibility": "public",
            "async": False,
        },
        {
            "name": "fetch",
            "type": "async_function",
            "file": "module.py",
            "line": 7,
            "end_line": 8,
            "parent": None,
            "decorators": [],
            "visibility": "public",
            "async": True,
        },
        {
            "name": "PublicClass",
            "type": "class",
            "file": "module.py",
            "line": 11,
            "end_line": 17,
            "parent": None,
            "decorators": ["dataclass"],
            "visibility": "public",
            "async": False,
        },
        {
            "name": "build",
            "type": "method",
            "file": "module.py",
            "line": 13,
            "end_line": 14,
            "parent": "PublicClass",
            "decorators": ["staticmethod"],
            "visibility": "public",
            "async": False,
        },
        {
            "name": "_load",
            "type": "method",
            "file": "module.py",
            "line": 16,
            "end_line": 17,
            "parent": "PublicClass",
            "decorators": [],
            "visibility": "private",
            "async": True,
        },
    ]
    assert any(
        reference["kind"] == "method_call"
        and reference["target"] == "PublicClass.build"
        for reference in understanding["references"]
    )


def test_codebase_resolves_local_packages_src_modules_and_dependencies(
    tmp_path: Path,
):
    (tmp_path / "pkg" / "nested").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "root_helper.py").write_text(
        "def invoke():\n    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "nested" / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "nested" / "tool.py").write_text(
        "def tool():\n    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "feature.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "client.py").write_text(
        "import root_helper as helper\n"
        "from pkg.nested import tool\n"
        "import feature\n"
        "import os\n"
        "import requests\n"
        "from .missing import value\n"
        "helper.invoke()\n",
        encoding="utf-8",
    )

    understanding = analyze(tmp_path)["codebase_understanding"]
    graph = understanding["dependency_graph"]["pkg/client.py"]

    assert graph == {
        "local": [
            "pkg/nested/tool.py",
            "root_helper.py",
            "src/feature.py",
        ],
        "external": ["requests"],
        "standard_library": ["os"],
        "unresolved": ["pkg.missing"],
    }
    relationships = understanding["relationships"]
    assert {
        (relationship["target"], relationship["dependency_type"])
        for relationship in relationships
        if relationship["source"] == "pkg/client.py"
    } == {
        ("root_helper.py", "local"),
        ("pkg/nested/tool.py", "local"),
        ("src/feature.py", "local"),
        ("os", "standard_library"),
        ("requests", "third_party"),
        ("pkg.missing", "unresolved"),
    }
    assert any(
        reference["kind"] == "imported_member_call"
        and reference["target"] == "helper.invoke"
        and reference["target_file"] == "root_helper.py"
        for reference in understanding["references"]
    )


def test_codebase_entry_points_components_and_summaries_are_structural(
    tmp_path: Path,
):
    (tmp_path / "app" / "api").mkdir(parents=True)
    (tmp_path / "app" / "services").mkdir()
    (tmp_path / "app" / "repositories").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "frontend").mkdir()
    for package in (
        tmp_path / "app" / "__init__.py",
        tmp_path / "app" / "api" / "__init__.py",
        tmp_path / "app" / "services" / "__init__.py",
        tmp_path / "app" / "repositories" / "__init__.py",
    ):
        package.write_text("", encoding="utf-8")
    (tmp_path / "app" / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "from app.api.routes import router\n"
        "app = FastAPI()\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "api" / "routes.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "services" / "worker.py").write_text(
        "def work():\n    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "repositories" / "items.py").write_text(
        "class ItemRepository:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_worker.py").write_text(
        "def test_work():\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "frontend" / "main.ts").write_text(
        "export const page = 'home';\n",
        encoding="utf-8",
    )
    (tmp_path / "pytest.ini").write_text("", encoding="utf-8")

    understanding = analyze(tmp_path)["codebase_understanding"]

    file = next(
        file
        for file in understanding["files"]
        if file["path"] == "app/main.py"
    )
    assert file == {
        "path": "app/main.py",
        "language": "python",
        "file_type": "source",
        "is_test": False,
        "is_entry_point": True,
        "module": "app.main",
    }
    assert understanding["test_files"] == ["tests/test_worker.py"]
    assert understanding["configuration_files"] == ["pytest.ini"]
    assert {tuple(item["roles"]) for item in understanding["important_files"]} >= {
        ("entry_point",),
        ("test",),
        ("configuration",),
    }

    entry_point = understanding["entry_point_context"]
    assert entry_point == [
        {
            "path": "app/main.py",
            "module": "app.main",
            "frameworks": ["FastAPI"],
            "symbols": ["app"],
            "imports": ["app.api.routes", "fastapi"],
            "local_imports": ["app/api/routes.py"],
        }
    ]
    component_names = [component["name"] for component in understanding["components"]]
    assert component_names == [
        "backend",
        "frontend",
        "python_package",
        "api",
        "configuration",
        "repository",
        "services",
        "tests",
    ]
    summary = understanding["summaries"]["app/services/worker.py"]
    assert summary == {
        "language": "python",
        "role": "service",
        "frameworks": [],
        "classes": [],
        "functions": ["work"],
        "imports": [],
        "parse_status": "parsed",
    }
    assert "return True" not in str(understanding["summaries"])


def test_codebase_context_reuses_completed_analysis_for_lookups(
    tmp_path: Path,
):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "dependency.py").write_text(
        "class Dependency:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "main.py").write_text(
        "from pkg.dependency import Dependency as Injected\n"
        "\n"
        "def run():\n"
        "    return Injected()\n",
        encoding="utf-8",
    )

    analyzer = RepositoryAnalyzer(RepositoryService(tmp_path))
    analyzer.analyze()
    context = analyzer.get_codebase_context()

    assert [symbol["file"] for symbol in context.symbols_named("Dependency")] == [
        "pkg/dependency.py"
    ]
    assert [symbol["name"] for symbol in context.symbols_in_file("pkg/main.py")] == [
        "run"
    ]
    assert context.module("pkg.main")["path"] == "pkg/main.py"
    assert context.modules_imported_by("pkg/main.py") == ["pkg.dependency"]
    assert context.modules_importing("pkg.dependency") == ["pkg/main.py"]
    assert context.local_dependencies("pkg.main") == ["pkg/dependency.py"]
    assert context.local_dependents("pkg/dependency.py") == ["pkg/main.py"]
    assert context.entry_point("pkg/main.py")["path"] == "pkg/main.py"
    assert context.entry_point("pkg.main")["path"] == "pkg/main.py"
    assert context.focused(file_path="pkg/main.py")["local_dependencies"] == [
        "pkg/dependency.py"
    ]
    assert context.focused(module_name="pkg.main")["entry_point"] is not None
    assert any(
        reference["kind"] == "imported_symbol_call"
        and reference["target"] == "Injected"
        and reference["target_file"] == "pkg/dependency.py"
        for reference in context.understanding["references"]
    )


def test_codebase_is_deterministic_and_safe_for_empty_invalid_and_unreadable_files(
    tmp_path: Path,
    monkeypatch,
):
    empty_result = analyze(tmp_path)["codebase_understanding"]
    assert empty_result == {
        "files": [],
        "modules": [],
        "symbols": [],
        "relationships": [],
        "dependency_graph": {},
        "references": [],
        "entry_point_context": [],
        "components": [],
        "layers": [],
        "test_files": [],
        "configuration_files": [],
        "important_files": [],
        "summaries": {},
    }

    (tmp_path / "empty.py").write_text("", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    (tmp_path / "unreadable.py").write_text(
        "def hidden():\n    pass\n",
        encoding="utf-8",
    )

    original_reader = RepositoryAnalyzer._read_source_file

    def unreadable_reader(path):
        if path.name == "unreadable.py":
            return None
        return original_reader(path)

    monkeypatch.setattr(
        RepositoryAnalyzer,
        "_read_source_file",
        staticmethod(unreadable_reader),
    )
    first = analyze(tmp_path)["codebase_understanding"]
    second = analyze(tmp_path)["codebase_understanding"]

    assert first == second
    modules = {module["path"]: module for module in first["modules"]}
    assert modules["empty.py"]["parse_status"] == "parsed"
    assert modules["broken.py"]["parse_status"] == "invalid"
    assert modules["unreadable.py"]["parse_status"] == "unreadable"
    assert modules["broken.py"]["functions"] == []
    assert modules["unreadable.py"]["imports"] == []
