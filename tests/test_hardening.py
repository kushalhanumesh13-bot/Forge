import json
from pathlib import Path

import pytest

from app.services.analyzer import RepositoryAnalyzer
from app.services.engineering_brain import EngineeringBrain
from app.services.repository import RepositoryService


def test_repository_service_skips_symlink_files_and_sorts_paths(tmp_path: Path):
    (tmp_path / "z.py").write_text("", encoding="utf-8")
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("SECRET = 'outside'\n", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        outside.unlink()
        pytest.skip("symbolic links are unavailable in this environment")

    try:
        files = RepositoryService(tmp_path).get_files()
        assert [path.name for path in files] == ["a.py", "z.py"]
        result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()
        assert "linked.py" not in result["index"]["files"]
    finally:
        outside.unlink(missing_ok=True)


def test_repository_root_name_does_not_trigger_directory_ignore(tmp_path: Path):
    root = tmp_path / "Git"
    root.mkdir()
    (root / "kept.py").write_text("", encoding="utf-8")

    assert [path.name for path in RepositoryService(root).get_files()] == [
        "kept.py"
    ]


def test_repository_service_does_not_follow_symlink_directories(tmp_path: Path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-dir"
    outside.mkdir()
    (outside / "secret.py").write_text("", encoding="utf-8")
    link = tmp_path / "linked-dir"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        (outside / "secret.py").unlink()
        outside.rmdir()
        pytest.skip("symbolic links are unavailable in this environment")

    try:
        assert all("secret.py" not in path.parts for path in RepositoryService(tmp_path).get_files())
    finally:
        (outside / "secret.py").unlink(missing_ok=True)
        outside.rmdir()


def test_codebase_context_lookup_results_cannot_mutate_cached_model(tmp_path: Path):
    (tmp_path / "module.py").write_text(
        "class Service:\n    pass\n",
        encoding="utf-8",
    )
    analyzer = RepositoryAnalyzer(RepositoryService(tmp_path))
    analyzer.analyze()
    context = analyzer.get_codebase_context()

    symbol = context.symbols_named("Service")[0]
    symbol["name"] = "Changed"
    module = context.module("module")
    module["path"] = "outside.py"
    understanding = context.understanding
    understanding["symbols"][0]["name"] = "ChangedPublicModel"
    focused = context.focused(file_path="module.py")
    focused["symbols"][0]["name"] = "ChangedAgain"

    assert context.symbols_named("Service")[0]["name"] == "Service"
    assert context.module("module")["path"] == "module.py"
    assert context.symbols_in_file("module.py")[0]["name"] == "Service"
    assert context.understanding["symbols"][0]["name"] == "Service"


def test_ambiguous_local_module_is_not_labeled_third_party(tmp_path: Path):
    (tmp_path / "foo").mkdir()
    (tmp_path / "foo.py").write_text("", encoding="utf-8")
    (tmp_path / "foo" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "main.py").write_text("import foo\n", encoding="utf-8")

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()
    graph = result["codebase_understanding"]["dependency_graph"]["main.py"]

    assert graph["local"] == []
    assert graph["external"] == []
    assert graph["unresolved"] == ["foo"]


def test_engineering_brain_hardening_is_explainable_and_serializable(tmp_path: Path):
    (tmp_path / "service.py").write_text(
        "def process():\n    return True\n",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "from service import process\n\nprocess()\n",
        encoding="utf-8",
    )
    analysis = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()
    brain = EngineeringBrain(analysis)

    assert brain.classify_task("Fixation is unrelated to defects")["type"] == "unknown"
    plan = brain.generate_plan(
        {"description": "Fix service processing", "targets": ["service.py"]}
    )
    assert any(
        reason == "local dependent of target module"
        for item in plan["context"]["ranked_files"]
        for reason in item["reasons"]
    )
    assert any(risk["type"] == "public_api_change" for risk in plan["risks"])
    assert len(brain.parse_task("x" * 200_000)["description"]) == 100_000
    json.dumps(plan)


def test_oversized_python_source_is_not_loaded_for_ast_analysis(tmp_path: Path):
    source = tmp_path / "large.py"
    source.write_bytes(b"x = 1\n" + b"# padding\n" * (2 * 1024 * 1024))

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    module = result["codebase_understanding"]["modules"][0]
    assert module["path"] == "large.py"
    assert module["parse_status"] == "unreadable"
    assert module["functions"] == []


def test_oversized_metadata_is_ignored_without_breaking_json_output(tmp_path: Path):
    (tmp_path / "README.md").write_bytes(b"# Large\n" + b"x" * (5 * 1024 * 1024))
    (tmp_path / "requirements.txt").write_bytes(b"requests\n" + b"x" * (5 * 1024 * 1024))

    result = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    assert result["readme"]["title"] is None
    assert result["dependencies"] == []
    json.dumps(result)