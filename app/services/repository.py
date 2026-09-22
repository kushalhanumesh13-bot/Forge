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
            try:
                relative_path = path.relative_to(self.root_path)
                current = self.root_path
                if any(
                    (current := current / part).is_symlink()
                    for part in relative_path.parts[:-1]
                ):
                    continue
                if (
                    path.is_symlink()
                    or not path.is_file()
                    or self._is_ignored(path)
                ):
                    continue
            except OSError:
                continue
            files.append(path)

        return sorted(files, key=lambda path: path.relative_to(self.root_path).as_posix())

    def _is_ignored(self, path: Path) -> bool:
        try:
            relative_parts = path.relative_to(self.root_path).parts
        except ValueError:
            return True

        ignored_directories = {directory.lower() for directory in IGNORED_DIRECTORIES}
        if any(part.lower() in ignored_directories for part in relative_parts[:-1]):
            return True

        ignored_files = {filename.lower() for filename in IGNORED_FILES}
        if path.name.lower() in ignored_files:
            return True

        return False
        