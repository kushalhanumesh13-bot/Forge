from app.services.repository import RepositoryService


class RepositoryAnalyzer:
    def __init__(self, repository: RepositoryService):
        self.repository = repository

    def analyze(self) -> dict:
        files = self.repository.get_files()

        python_files = 0
        javascript_files = 0
        typescript_files = 0
        test_files = 0
        other_files = 0
        directories = set()

        for path in files:
            relative_path = path.relative_to(self.repository.root_path)

            if len(relative_path.parts) > 1:
                directories.add(relative_path.parts[0])

            if path.suffix == ".py":
                python_files += 1
            elif path.suffix == ".js":
                javascript_files += 1
            elif path.suffix == ".ts":
                typescript_files += 1
            else:
                other_files += 1

            if "test" in path.name.lower():
                test_files += 1

        project_type = self._detect_project_type(
            python_files=python_files,
            javascript_files=javascript_files,
            typescript_files=typescript_files,
        )

        return {
            "summary": {
                "total_files": len(files),
                "python_files": python_files,
                "javascript_files": javascript_files,
                "typescript_files": typescript_files,
                "test_files": test_files,
                "other_files": other_files,
            },
            "project_type": project_type,
            "has_tests": test_files > 0,
            "directories": sorted(directories),
        }

    def _detect_project_type(
        self,
        python_files: int,
        javascript_files: int,
        typescript_files: int,
    ) -> str:
        if python_files > 0:
            return "python"

        if typescript_files > 0:
            return "typescript"

        if javascript_files > 0:
            return "javascript"

        return "unknown"