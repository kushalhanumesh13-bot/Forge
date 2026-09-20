from pathlib import Path

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

    repository = RepositoryService(root_path=tmp_path)
    analyzer = RepositoryAnalyzer(repository)

    result = analyzer.analyze()

    assert result["summary"]["total_files"] == 6
    assert result["summary"]["python_files"] == 3
    assert result["summary"]["javascript_files"] == 1
    assert result["summary"]["typescript_files"] == 1
    assert result["summary"]["test_files"] == 1
    assert result["summary"]["other_files"] == 1

    assert result["project_type"] == "python"
    assert result["has_tests"] is True
    assert result["directories"] == ["app", "tests"]
    assert result["metadata_files"] == ["pyproject.toml"]

