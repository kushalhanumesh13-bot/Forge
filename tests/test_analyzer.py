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

    assert result["total_files"] == 5
    assert result["python_files"] == 3
    assert result["javascript_files"] == 1
    assert result["typescript_files"] == 1
    assert result["test_files"] == 1
    assert result["other_files"] == 0