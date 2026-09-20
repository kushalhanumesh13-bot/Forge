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

        for path in files:
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

        return {
            "total_files": len(files),
            "python_files": python_files,
            "javascript_files": javascript_files,
            "typescript_files": typescript_files,
            "test_files": test_files,
            "other_files": other_files,
        }