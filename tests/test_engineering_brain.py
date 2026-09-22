from pathlib import Path

from app.services.analyzer import RepositoryAnalyzer
from app.services.engineering_brain import EngineeringBrain
from app.services.repository import RepositoryService


def build_analysis(tmp_path: Path) -> dict:
    (tmp_path / "app" / "services").mkdir(parents=True)
    (tmp_path / "app" / "api").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "app" / "services" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (tmp_path / "app" / "api" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (tmp_path / "app" / "main.py").write_text(
        "from app.services.repository import RepositoryService\n"
        "app = RepositoryService()\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "services" / "repository.py").write_text(
        "class RepositoryService:\n"
        "    def scan(self):\n"
        "        return True\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "services" / "worker.py").write_text(
        "from app.services.repository import RepositoryService\n\n"
        "def process_repository():\n"
        "    return RepositoryService().scan()\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_repository.py").write_text(
        "def test_repository_scan():\n    assert True\n",
        encoding="utf-8",
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    return RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()


def test_task_model_normalizes_input_and_classifies_explicit_type(tmp_path: Path):
    brain = EngineeringBrain(build_analysis(tmp_path))

    task = brain.parse_task(
        {
            "description": "  Add repository scanning support\n",
            "type": "feature",
            "targets": ["app/services/repository.py", "app/services/repository.py"],
            "constraints": ["Keep API stable"],
        }
    )

    assert task["description"] == "Add repository scanning support"
    assert task["type"] == "feature"
    assert task["confidence"] == "high"
    assert task["targets"] == ["app/services/repository.py"]
    assert task["constraints"] == ["Keep API stable"]


def test_classification_covers_categories_and_unknown_tasks(tmp_path: Path):
    brain = EngineeringBrain(build_analysis(tmp_path))

    assert brain.classify_task("Fix the broken repository scan")["type"] == "bug_fix"
    assert brain.classify_task("Refactor the worker service")["type"] == "refactor"
    assert brain.classify_task("Add pytest coverage")["type"] == "test"
    assert brain.classify_task("Update the README documentation")["type"] == "documentation"
    assert brain.classify_task("Change configuration settings")["type"] == "configuration"
    assert brain.classify_task("Investigate repository behavior")["type"] == "investigation"
    assert brain.classify_task("Make the repository nicer")["type"] == "unknown"


def test_scope_ranking_and_context_use_repository_evidence(tmp_path: Path):
    brain = EngineeringBrain(build_analysis(tmp_path))

    context = brain.retrieve_context(
        {
            "description": "Fix repository scanning",
            "targets": ["app/services/repository.py"],
        }
    )

    assert context["ranked_files"][0]["path"] == "app/services/repository.py"
    assert context["ranked_files"][0]["score"] >= 10
    assert any("exact target file match" in reason for reason in context["ranked_files"][0]["reasons"])
    assert "return True" not in str(context)
    assert "app/services/repository.py" in context["summaries"]

    scope = brain.analyze_scope(
        {
            "description": "Fix repository scanning",
            "targets": ["app/services/repository.py"],
        }
    )
    assert "app/services/repository.py" in scope["relevant_files"]
    assert "RepositoryService" in [symbol["name"] for symbol in scope["relevant_symbols"]]


def test_impact_finds_dependencies_dependents_tests_and_entry_points(tmp_path: Path):
    brain = EngineeringBrain(build_analysis(tmp_path))
    task = {"description": "Refactor repository service", "targets": ["app/services/repository.py"]}
    scope = brain.analyze_scope(task)
    impact = brain.analyze_impact(task, scope)

    assert impact["direct_targets"] == ["app/services/repository.py"]
    assert "app/services/worker.py" in impact["dependents"]
    assert "app/main.py" in impact["dependents"]
    assert "repository" in impact["components"]


def test_ambiguity_and_risks_are_explicit(tmp_path: Path):
    brain = EngineeringBrain(build_analysis(tmp_path))

    vague = brain.generate_plan("Make it better")
    assert vague["ambiguity"]["needs_clarification"] is True
    assert any(risk["type"] == "ambiguous_task_scope" for risk in vague["risks"])

    targeted = brain.generate_plan(
        {"description": "Fix repository service", "targets": ["app/services/repository.py"]}
    )
    assert targeted["ambiguity"]["needs_clarification"] is False
    assert targeted["confidence"] in {"medium", "high"}


def test_plan_contains_ordered_steps_test_strategy_and_assumptions(tmp_path: Path):
    brain = EngineeringBrain(build_analysis(tmp_path))
    plan = brain.generate_plan(
        {
            "description": "Add repository scanning behavior",
            "targets": ["app/services/repository.py"],
            "acceptance_criteria": ["Existing API remains compatible"],
        }
    )

    assert plan["objective"] == "Add repository scanning behavior"
    assert plan["affected_files"] == ["app/services/repository.py"]
    assert [step["order"] for step in plan["steps"]] == [1, 2, 3, 4]
    assert plan["steps"][1]["depends_on"] == [1]
    assert "tests/test_repository.py" in plan["tests"]["existing_tests"]
    assert plan["validation"] == ["python -m pytest -q"]
    assert plan["assumptions"]


def test_plan_is_deterministic_and_empty_repository_is_safe(tmp_path: Path):
    empty_brain = EngineeringBrain(
        RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()
    )
    empty_plan = empty_brain.generate_plan("")
    assert empty_plan["ambiguity"]["needs_clarification"] is True
    assert empty_plan["affected_files"] == []
    assert empty_plan["steps"][0]["depends_on"] == []

    analysis = build_analysis(tmp_path / "project")
    first = EngineeringBrain(analysis).generate_plan("Fix repository service")
    second = EngineeringBrain(analysis).generate_plan("Fix repository service")
    assert first == second


def test_invalid_python_does_not_break_brain(tmp_path: Path):
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    analysis = RepositoryAnalyzer(RepositoryService(tmp_path)).analyze()

    result = EngineeringBrain(analysis).generate_plan("Investigate broken module")

    assert result["task"]["type"] == "investigation"
    assert result["context"]["summaries"]["broken.py"]["parse_status"] == "invalid"