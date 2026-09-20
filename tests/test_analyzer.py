from pathlib import Path

from app.services.analyzer import RepositoryAnalyzer
from app.services.repository import RepositoryService


def test_analyze_counts_file_types(tmp_path: Path):
    (tmp_path / "main.py").write_text("")
    (tmp_path / "app.py").write_text("")
    (tmp_path / "script.js").write_text("")
    (tmp_path / "types.ts").write_text("")
    (tmp_path / "test_main.py").write_text("")

    repository = RepositoryService(root_path=tmp_path)
    analyzer = RepositoryAnalyzer(repository)

    result = analyzer.analyze()

    assert result["summary"]["total_files"] == 5
    assert result["summary"]["python_files"] == 3
    assert result["summary"]["javascript_files"] == 1
    assert result["summary"]["typescript_files"] == 1
    assert result["summary"]["test_files"] == 1
    assert result["summary"]["other_files"] == 0

    assert result["project_type"] == "python"
    assert result["has_tests"] is True