from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "Git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
}

IGNORED_FILES = {
    ".env",
    ".env.local",
}


class RepositoryService:
    def __init__(self, root_path: Path):
        self.root_path = root_path

    def get_files(self) -> list[Path]:
        files = []

        for path in self.root_path.rglob("*"):
            if path.is_file() and not self._is_ignored(path):
                files.append(path)

        return files

    def _is_ignored(self, path: Path) -> bool:
        for ignored_dir in IGNORED_DIRECTORIES:
            if ignored_dir in path.parts:
                return True

        for ignored_file in IGNORED_FILES:
            if path.name == ignored_file:
                return True

        return False
        