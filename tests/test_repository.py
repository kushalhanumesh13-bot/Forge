from pathlib import Path

from app.services.repository import RepositoryService

def test_get_files_ignores_ignored_directories(tmp_path: Path):
    # Create a temporary directory structure
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored_file.txt").write_text("This file should be ignored.")
    (tmp_path / "valid_file.txt").write_text("This file should be included.")

    service = RepositoryService(root_path=tmp_path)
    files = service.get_files()

    assert len(files) == 1
    assert files[0].name == "valid_file.txt"