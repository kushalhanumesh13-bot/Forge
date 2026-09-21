import ast
import json
import re
import subprocess
import sys
import tomllib

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
        metadata_files = []
        technologies = set()
        frameworks = set()
        dependencies = set()
        lockfiles = []
        entry_points = set()
        configurations = set()
        imports = {}
        code_structure = {}
        architecture = {}
        git_info = self._analyze_git()

        readme_info = {
            "present": False,
            "path": None,
            "title": None,
            "description": None,
            "sections": [],
        }

        metadata_names = {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "README.md",
            "Dockerfile",
            ".gitignore",
        }

        configuration_names = {
            ".env.example",
            ".env.template",
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
            "tsconfig.json",
            "vite.config.js",
            "vite.config.ts",
            "webpack.config.js",
            "webpack.config.ts",
            "pytest.ini",
            "tox.ini",
            "ruff.toml",
            ".mypy.ini",
        }

        technology_names = {
            "requirements.txt": "Python",
            "pyproject.toml": "Python",
            "package.json": "JavaScript/Node.js",
            "Dockerfile": "Docker",
        }

        python_module_roots = self._python_module_roots(files)

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

            if path.name in metadata_names:
                metadata_files.append(str(relative_path))

                if path.name in technology_names:
                    technologies.add(technology_names[path.name])

            if path.name in configuration_names:
                configurations.add(relative_path.as_posix())

            if path.name.lower() == "readme.md":
                readme_info = self._analyze_readme(
                    path,
                    relative_path,
                )

            dependency_kind = self._dependency_file_kind(path.name)

            if dependency_kind == "lockfile":
                lockfiles.append(str(relative_path))

            elif dependency_kind:
                dependency_content = self._read_dependency_file(path)

                dependencies.update(
                    self._detect_dependencies(
                        dependency_kind,
                        dependency_content,
                    )
                )

                if dependency_kind == "package":
                    entry_points.update(
                        self._detect_package_entry_points(
                            path,
                            dependency_content,
                            files,
                        )
                    )

            if path.suffix in {".py", ".js", ".ts"}:
                content = path.read_text(encoding="utf-8")

                if path.suffix == ".py":
                    imports[relative_path.as_posix()] = (
                        self._analyze_python_imports(
                            content,
                            python_module_roots,
                        )
                    )
                    code_structure[relative_path.as_posix()] = (
                        self._analyze_python_code_structure(content)
                    )

                if path.suffix == ".py" and (
                    path.name in {"main.py", "__main__.py"}
                    or self._contains_python_main_guard(content)
                ):
                    entry_points.add(
                        relative_path.as_posix()
                    )

                detected_frameworks = self._detect_frameworks(
                    content=content,
                    suffix=path.suffix,
                )

                frameworks.update(detected_frameworks)
                technologies.update(detected_frameworks)

        project_type = self._detect_project_type(
            python_files=python_files,
            javascript_files=javascript_files,
            typescript_files=typescript_files,
        )

        architecture = self._detect_architecture(
            files=files,
            frameworks=frameworks,
            entry_points=entry_points,
            configurations=configurations,
            imports=imports,
            code_structure=code_structure,
            test_files=test_files,
            python_files=python_files,
            javascript_files=javascript_files,
            typescript_files=typescript_files,
        )

        index = self._build_repository_index(
            files=files,
            metadata_files=metadata_files,
            configurations=configurations,
            lockfiles=lockfiles,
            imports=imports,
            code_structure=code_structure,
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
            "metadata_files": sorted(metadata_files),
            "technologies": sorted(technologies),
            "frameworks": sorted(frameworks),
            "dependencies": sorted(dependencies),
            "lockfiles": sorted(lockfiles),
            "entry_points": sorted(entry_points),
            "configurations": sorted(configurations),
            "readme": readme_info,
            "git": git_info,
            "imports": dict(sorted(imports.items())),
            "code_structure": dict(sorted(code_structure.items())),
            "architecture": architecture,
            "index": index,
        }

    def _build_repository_index(
        self,
        files: list,
        metadata_files: list[str],
        configurations: set[str],
        lockfiles: list[str],
        imports: dict,
        code_structure: dict,
    ) -> dict:
        metadata_paths = {
            path.replace("\\", "/")
            for path in metadata_files
        }
        lockfile_paths = {
            path.replace("\\", "/")
            for path in lockfiles
        }
        configuration_paths = set(configurations)
        indexed_files = []

        language_by_suffix = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
        }

        for path in files:
            relative_path = path.relative_to(self.repository.root_path).as_posix()
            language = language_by_suffix.get(path.suffix, "other")

            if relative_path in configuration_paths:
                file_type = "configuration"
            elif relative_path in lockfile_paths:
                file_type = "lockfile"
            elif relative_path in metadata_paths:
                file_type = "metadata"
            elif language != "other":
                file_type = "source"
            else:
                file_type = "other"

            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = None

            record = {
                "path": relative_path,
                "language": language,
                "file_type": file_type,
                "is_test": "test" in path.name.lower(),
                "size_bytes": size_bytes,
            }

            if path.suffix == ".py":
                import_info = imports.get(relative_path, {})
                record["imports"] = import_info.get("imports", [])
                record["structure"] = code_structure.get(
                    relative_path,
                    {
                        "classes": [],
                        "functions": [],
                        "methods": [],
                        "constants": [],
                        "global_assignments": [],
                    },
                )

            indexed_files.append(record)

        indexed_files.sort(key=lambda record: record["path"])

        return {
            "files": indexed_files,
            "total_files": len(indexed_files),
        }

    def _detect_architecture(
        self,
        files: list,
        frameworks: set[str],
        entry_points: set[str],
        configurations: set[str],
        imports: dict,
        code_structure: dict,
        test_files: int,
        python_files: int,
        javascript_files: int,
        typescript_files: int,
    ) -> dict:
        layers = set()
        components = set()
        evidence = []

        source_paths = {
            path.relative_to(self.repository.root_path).as_posix(): path
            for path in files
            if path.suffix in {".py", ".js", ".ts"}
        }

        def paths_with_component(names: set[str]) -> list[str]:
            return sorted(
                path
                for path in source_paths
                if any(
                    part.lower() in names
                    for part in (
                        path.split("/")
                        + [source_paths[path].stem]
                    )
                )
            )

        api_paths = paths_with_component({"api", "routes", "routers", "controllers"})
        service_paths = paths_with_component({"service", "services"})
        repository_paths = paths_with_component(
            {"repository", "repositories", "data", "persistence", "dao"}
        )
        test_paths = sorted(
            path
            for path in source_paths
            if "test" in source_paths[path].name.lower()
            or "tests" in {part.lower() for part in path.split("/")}
        )
        frontend_paths = sorted(
            path
            for path in source_paths
            if any(
                part.lower() in {"frontend", "client", "web", "ui"}
                for part in path.split("/")
            )
        )
        backend_paths = sorted(
            path
            for path in source_paths
            if any(
                part.lower() in {"backend", "server"}
                for part in path.split("/")
            )
        )

        api_signal = bool(api_paths) and (
            bool(frameworks & {"FastAPI", "Django", "Flask"})
            or any(imports.get(path, {}).get("imports") for path in api_paths)
        )
        service_signal = bool(service_paths) and any(
            code_structure.get(path, {}).get("classes")
            or code_structure.get(path, {}).get("functions")
            for path in service_paths
        )
        repository_signal = bool(repository_paths) and any(
            code_structure.get(path, {}).get("classes")
            or code_structure.get(path, {}).get("functions")
            or code_structure.get(path, {}).get("methods")
            for path in repository_paths
        )

        if api_signal:
            layers.add("api")
            evidence.append(
                "API source files have framework or import evidence: "
                + ", ".join(api_paths)
            )

        if service_signal:
            layers.add("services")
            evidence.append(
                "Service source files contain detected classes or functions: "
                + ", ".join(service_paths)
            )

        if repository_signal:
            layers.add("repository")
            evidence.append(
                "Repository/data-access source files contain detected code: "
                + ", ".join(repository_paths)
            )

        if test_files > 0 and test_paths:
            layers.add("tests")
            evidence.append(
                "Test source files were detected: " + ", ".join(test_paths)
            )

        if configurations:
            layers.add("configuration")
            evidence.append(
                "Recognized configuration files were detected: "
                + ", ".join(sorted(configurations))
            )

        has_python_package = python_files >= 2 and any(
            path.name == "__init__.py"
            for path in source_paths.values()
        )
        if has_python_package:
            components.add("python_package")
            evidence.append(
                "Multiple Python files include package initializer files"
            )

        has_backend = bool(backend_paths) or bool(
            python_files and (api_signal or service_signal or repository_signal)
        )
        has_frontend = bool(frontend_paths) and bool(
            javascript_files or typescript_files
        )

        if has_backend:
            components.add("backend")
        if has_frontend:
            components.add("frontend")

        if has_frontend and has_backend:
            style = "frontend-backend"
            evidence.append(
                "Separate frontend and backend source areas have language evidence"
            )
        elif len(layers & {"api", "services", "repository"}) >= 2:
            style = "layered"
            evidence.append(
                "Multiple application layers have independent code evidence"
            )
        elif has_backend and entry_points:
            style = "monolithic"
            evidence.append(
                "Backend application code and entry-point candidates are present"
            )
        else:
            style = "unknown"

        return {
            "style": style,
            "layers": sorted(layers),
            "components": sorted(components),
            "evidence": sorted(evidence),
        }

    def _python_module_roots(self, files: list) -> set[str]:
        module_roots = set()

        for path in files:
            if path.suffix != ".py":
                continue

            relative_path = path.relative_to(self.repository.root_path)

            if len(relative_path.parts) > 1:
                module_roots.add(relative_path.parts[0])
            elif path.stem != "__init__":
                module_roots.add(path.stem)

        return module_roots

    def _analyze_python_imports(
        self,
        content: str,
        local_module_roots: set[str],
    ) -> dict:
        result = {
            "imports": [],
            "standard_library": [],
            "third_party": [],
            "local_project": [],
        }

        try:
            tree = ast.parse(content)
        except (SyntaxError, UnicodeError):
            return result

        imported_modules = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(
                    alias.name
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                imported_modules.add(
                    "." * node.level + module_name
                )

        standard_library = set()
        third_party = set()
        local_project = set()

        for module_name in imported_modules:
            root_name = module_name.lstrip(".").split(".", 1)[0]

            if module_name.startswith(".") or root_name in local_module_roots:
                local_project.add(module_name)
            elif root_name in sys.stdlib_module_names:
                standard_library.add(module_name)
            else:
                third_party.add(module_name)

        result["imports"] = sorted(imported_modules)
        result["standard_library"] = sorted(standard_library)
        result["third_party"] = sorted(third_party)
        result["local_project"] = sorted(local_project)

        return result

    def _analyze_python_code_structure(self, content: str) -> dict:
        result = {
            "classes": [],
            "functions": [],
            "methods": [],
            "constants": [],
            "global_assignments": [],
        }

        try:
            tree = ast.parse(content)
        except (SyntaxError, UnicodeError):
            return result

        classes = []
        functions = []
        methods = []
        global_assignments = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(self._structure_definition(node))
                self._collect_python_methods(
                    node,
                    node.name,
                    methods,
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._structure_definition(node))
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                for name in self._assignment_names(node):
                    global_assignments.append(
                        {
                            "name": name,
                            "line": node.lineno,
                        }
                    )

        constants = [
            assignment
            for assignment in global_assignments
            if assignment["name"].isupper()
        ]

        result["classes"] = sorted(
            classes,
            key=lambda item: (item["line"], item["name"]),
        )
        result["functions"] = sorted(
            functions,
            key=lambda item: (item["line"], item["name"]),
        )
        result["methods"] = sorted(
            methods,
            key=lambda item: (item["line"], item["class"], item["name"]),
        )
        result["global_assignments"] = sorted(
            global_assignments,
            key=lambda item: (item["line"], item["name"]),
        )
        result["constants"] = sorted(
            constants,
            key=lambda item: (item["line"], item["name"]),
        )

        return result

    def _structure_definition(self, node) -> dict:
        return {
            "name": node.name,
            "line": node.lineno,
            "async": isinstance(node, ast.AsyncFunctionDef),
            "decorators": sorted(
                self._decorator_name(decorator)
                for decorator in node.decorator_list
            ),
        }

    def _collect_python_methods(
        self,
        class_node: ast.ClassDef,
        class_name: str,
        methods: list[dict],
    ) -> None:
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._structure_definition(node)
                method["class"] = class_name
                methods.append(method)
            elif isinstance(node, ast.ClassDef):
                self._collect_python_methods(
                    node,
                    f"{class_name}.{node.name}",
                    methods,
                )

    def _assignment_names(self, node) -> list[str]:
        targets = []

        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]

        names = []

        def collect(target) -> None:
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    collect(element)

        for target in targets:
            collect(target)

        return names

    def _decorator_name(self, decorator) -> str:
        try:
            return ast.unparse(decorator)
        except (AttributeError, ValueError):
            if isinstance(decorator, ast.Name):
                return decorator.id
            return type(decorator).__name__

    def _analyze_git(self) -> dict:
        result = {
            "is_repository": False,
            "branch": None,
            "commit": None,
            "is_clean": None,
            "changed_files": [],
            "remote": None,
        }

        git_directory = self.repository.root_path / ".git"

        if not git_directory.exists():
            return result

        result["is_repository"] = True

        result["branch"] = self._run_git_command(
            ["rev-parse", "--abbrev-ref", "HEAD"]
        )

        result["commit"] = self._run_git_command(
            ["rev-parse", "HEAD"]
        )

        status_output = self._run_git_command(
            ["status", "--porcelain"]
        )

        if status_output is not None:
            result["is_clean"] = status_output == ""
            result["changed_files"] = self._parse_git_status(
                status_output
            )

        remote = self._run_git_command(
            ["remote", "get-url", "origin"]
        )

        if remote:
            result["remote"] = remote

        return result

    def _run_git_command(self, arguments: list[str]) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=self.repository.root_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                check=False,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return None

        if completed.returncode != 0:
            return None

        return completed.stdout.strip()

    def _parse_git_status(self, output: str) -> list[str]:
        changed_files = []

        for line in output.splitlines():
            if len(line) < 4:
                continue

            path = line[2:].strip()

            if " -> " in path:
                path = path.split(" -> ", 1)[1]

            if path.startswith('"') and path.endswith('"'):
                path = path[1:-1]

            if path:
                changed_files.append(path.replace("\\", "/"))

        return sorted(set(changed_files))

    def _analyze_readme(self, path, relative_path) -> dict:
        result = {
            "present": True,
            "path": relative_path.as_posix(),
            "title": None,
            "description": None,
            "sections": [],
        }

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return result

        lines = content.splitlines()

        title_index = None

        for index, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("# ") and not stripped.startswith("## "):
                title = stripped[2:].strip()

                if title:
                    result["title"] = title
                    title_index = index
                    break

        description_lines = []

        start_index = (
            title_index + 1
            if title_index is not None
            else 0
        )

        for line in lines[start_index:]:
            stripped = line.strip()

            if stripped.startswith("#"):
                break

            if not stripped:
                if description_lines:
                    break

                continue

            if stripped.startswith(("![", "[", "<")):
                continue

            description_lines.append(stripped)

        if description_lines:
            result["description"] = " ".join(description_lines)

        sections = []

        for line in lines:
            stripped = line.strip()

            heading_match = re.match(
                r"^#{2,6}\s+(.+?)\s*#*$",
                stripped,
            )

            if heading_match:
                section = heading_match.group(1).strip()

                if section:
                    sections.append(section)

        result["sections"] = sections

        return result

    def _contains_python_main_guard(self, content: str) -> bool:
        try:
            tree = ast.parse(content)
        except (SyntaxError, UnicodeError):
            return False

        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                continue

            if (
                not isinstance(node.left, ast.Name)
                or node.left.id != "__name__"
            ):
                continue

            if (
                not isinstance(node.ops[0], ast.Eq)
                or len(node.comparators) != 1
            ):
                continue

            comparator = node.comparators[0]

            if (
                isinstance(comparator, ast.Constant)
                and comparator.value == "__main__"
            ):
                return True

        return False

    def _detect_package_entry_points(
        self,
        package_path,
        content: str,
        files: list,
    ) -> set[str]:
        document = self._parse_package_json(content)

        if not isinstance(document, dict):
            return set()

        values = []

        for field in ("main", "module"):
            values.append(document.get(field))

        bin_value = document.get("bin")

        if isinstance(bin_value, str):
            values.append(bin_value)
        elif isinstance(bin_value, dict):
            values.extend(bin_value.values())

        values.extend(
            self._package_export_values(
                document.get("exports")
            )
        )

        scanned_files = {
            path.resolve()
            for path in files
        }

        entry_points = set()

        for value in values:
            entry_point = self._resolve_entry_point(
                package_path,
                value,
                scanned_files,
            )

            if entry_point:
                entry_points.add(entry_point)

        return entry_points

    def _parse_package_json(self, content: str) -> dict | None:
        try:
            document = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None

        return document if isinstance(document, dict) else None

    def _package_export_values(self, value) -> list[str]:
        if isinstance(value, str):
            return [value]

        if isinstance(value, dict):
            values = []

            for nested_value in value.values():
                values.extend(
                    self._package_export_values(
                        nested_value
                    )
                )

            return values

        if isinstance(value, list):
            values = []

            for nested_value in value:
                values.extend(
                    self._package_export_values(
                        nested_value
                    )
                )

            return values

        return []

    def _resolve_entry_point(
        self,
        package_path,
        value,
        scanned_files,
    ) -> str | None:
        if not isinstance(value, str) or not value:
            return None

        normalized_value = value.replace("\\", "/")

        if normalized_value.startswith("/"):
            return None

        candidate = (
            package_path.parent / normalized_value
        ).resolve()

        if candidate not in scanned_files:
            return None

        try:
            relative_path = candidate.relative_to(
                self.repository.root_path.resolve()
            )
        except ValueError:
            return None

        return relative_path.as_posix()

    def _dependency_file_kind(
        self,
        filename: str,
    ) -> str | None:
        normalized_name = filename.lower()

        if normalized_name == "requirements.txt":
            return "requirements"

        if normalized_name == "pyproject.toml":
            return "pyproject"

        if normalized_name == "package.json":
            return "package"

        lockfile_names = {
            "bun.lock",
            "bun.lockb",
            "npm-shrinkwrap.json",
            "package-lock.json",
            "pipfile.lock",
            "pnpm-lock.yaml",
            "poetry.lock",
            "uv.lock",
            "yarn.lock",
        }

        if normalized_name in lockfile_names:
            return "lockfile"

        return None

    def _read_dependency_file(self, path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""

    def _detect_dependencies(
        self,
        kind: str,
        content: str,
    ) -> set[str]:
        if kind == "requirements":
            return self._detect_requirements_dependencies(content)

        if kind == "pyproject":
            return self._detect_pyproject_dependencies(content)

        if kind == "package":
            return self._detect_package_dependencies(content)

        return set()

    def _detect_requirements_dependencies(
        self,
        content: str,
    ) -> set[str]:
        dependencies = set()

        for line in content.splitlines():
            requirement = line.strip()

            if not requirement or requirement.startswith("#"):
                continue

            if requirement.startswith(("-r", "--", "-c")):
                continue

            egg_match = re.search(
                r"#egg=([A-Za-z0-9][A-Za-z0-9._-]*)",
                requirement,
            )

            if egg_match:
                dependencies.add(
                    egg_match.group(1).lower()
                )
                continue

            requirement = requirement.split(" #", 1)[0].strip()

            match = re.match(
                r"([A-Za-z0-9][A-Za-z0-9._-]*)",
                requirement,
            )

            if match:
                dependencies.add(
                    match.group(1).lower()
                )

        return dependencies

    def _detect_pyproject_dependencies(
        self,
        content: str,
    ) -> set[str]:
        try:
            document = tomllib.loads(content)
        except (tomllib.TOMLDecodeError, TypeError):
            return set()

        dependency_values = []

        project = document.get("project", {})

        if isinstance(project, dict):
            project_dependencies = project.get(
                "dependencies",
                [],
            )

            if isinstance(project_dependencies, list):
                dependency_values.extend(
                    project_dependencies
                )

            optional_dependencies = project.get(
                "optional-dependencies",
                {},
            )

            if isinstance(optional_dependencies, dict):
                for values in optional_dependencies.values():
                    if isinstance(values, list):
                        dependency_values.extend(values)

        tool = document.get("tool", {})

        poetry = (
            tool.get("poetry", {})
            if isinstance(tool, dict)
            else {}
        )

        if isinstance(poetry, dict):
            poetry_dependencies = poetry.get(
                "dependencies",
                {},
            )

            if isinstance(poetry_dependencies, dict):
                dependency_values.extend(
                    name
                    for name in poetry_dependencies
                    if name.lower() != "python"
                )

            poetry_dev_dependencies = poetry.get(
                "dev-dependencies",
                {},
            )

            if isinstance(
                poetry_dev_dependencies,
                dict,
            ):
                dependency_values.extend(
                    poetry_dev_dependencies
                )

        return {
            dependency
            for value in dependency_values
            if isinstance(value, str)
            for dependency in [
                self._dependency_name(value)
            ]
            if dependency
        }

    def _detect_package_dependencies(
        self,
        content: str,
    ) -> set[str]:
        try:
            document = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return set()

        dependencies = set()

        if not isinstance(document, dict):
            return dependencies

        sections = (
            "dependencies",
            "devDependencies",
            "optionalDependencies",
            "peerDependencies",
        )

        for section in sections:
            values = document.get(section, {})

            if isinstance(values, dict):
                dependencies.update(
                    name.lower()
                    for name in values
                    if isinstance(name, str)
                )

        return dependencies

    def _dependency_name(
        self,
        value: str,
    ) -> str | None:
        match = re.match(
            r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)",
            value,
        )

        return (
            match.group(1).lower()
            if match
            else None
        )

    def _detect_frameworks(
        self,
        content: str,
        suffix: str,
    ) -> set[str]:
        if suffix == ".py":
            return self._detect_python_frameworks(content)

        if suffix in {".js", ".ts"}:
            return self._detect_javascript_frameworks(content)

        return set()

    def _detect_python_frameworks(
        self,
        content: str,
    ) -> set[str]:
        try:
            tree = ast.parse(content)
        except (SyntaxError, UnicodeError):
            return set()

        frameworks = set()

        framework_names = {
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module_names = (
                    alias.name
                    for alias in node.names
                )

            elif (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and node.module
            ):
                module_names = (node.module,)

            else:
                continue

            for module_name in module_names:
                framework = framework_names.get(
                    module_name.split(".", 1)[0]
                )

                if framework:
                    frameworks.add(framework)

        return frameworks

    def _detect_javascript_frameworks(
        self,
        content: str,
    ) -> set[str]:
        tokens = self._tokenize_javascript(content)
        frameworks = set()

        for index, (token_type, token) in enumerate(tokens):
            if (
                token_type == "identifier"
                and token == "import"
            ):
                module_name = (
                    self._imported_module_name(
                        tokens,
                        index,
                    )
                )

            elif (
                token_type == "identifier"
                and token == "require"
            ):
                module_name = (
                    self._required_module_name(
                        tokens,
                        index,
                    )
                )

            else:
                continue

            if module_name == "react":
                frameworks.add("React")

            elif module_name == "express":
                frameworks.add("Express")

            elif module_name and (
                module_name == "next"
                or module_name.startswith("next/")
            ):
                frameworks.add("Next.js")

        return frameworks

    def _tokenize_javascript(
        self,
        content: str,
    ) -> list[tuple[str, str]]:
        tokens = []
        index = 0

        while index < len(content):
            character = content[index]

            if character.isspace():
                index += 1
                continue

            if content.startswith("//", index):
                newline = content.find(
                    "\n",
                    index + 2,
                )

                index = (
                    len(content)
                    if newline == -1
                    else newline + 1
                )

                continue

            if content.startswith("/*", index):
                comment_end = content.find(
                    "*/",
                    index + 2,
                )

                index = (
                    len(content)
                    if comment_end == -1
                    else comment_end + 2
                )

                continue

            if character in {"'", '"', "`"}:
                quote = character
                index += 1
                value = []

                while index < len(content):
                    character = content[index]

                    if (
                        character == "\\"
                        and index + 1 < len(content)
                    ):
                        value.append(
                            content[index + 1]
                        )
                        index += 2

                    elif character == quote:
                        index += 1
                        break

                    else:
                        value.append(character)
                        index += 1

                if quote != "`":
                    tokens.append(
                        (
                            "string",
                            "".join(value),
                        )
                    )

                continue

            if (
                character.isalpha()
                or character in {"_", "$"}
            ):
                start = index
                index += 1

                while index < len(content):
                    character = content[index]

                    if not (
                        character.isalnum()
                        or character in {"_", "$"}
                    ):
                        break

                    index += 1

                tokens.append(
                    (
                        "identifier",
                        content[start:index],
                    )
                )

                continue

            tokens.append(
                (
                    "symbol",
                    character,
                )
            )

            index += 1

        return tokens

    def _imported_module_name(
        self,
        tokens: list[tuple[str, str]],
        index: int,
    ) -> str | None:
        if (
            index + 1 >= len(tokens)
            or tokens[index + 1][1] == "("
        ):
            return None

        for offset, (token_type, token) in enumerate(
            tokens[index + 1:],
            start=index + 1,
        ):
            if token == ";":
                return None

            if (
                token_type == "identifier"
                and token == "from"
                and offset + 1 < len(tokens)
                and tokens[offset + 1][0] == "string"
            ):
                return tokens[offset + 1][1]

            if (
                offset == index + 1
                and token not in {"from"}
            ):
                continue

        return None

    def _required_module_name(
        self,
        tokens: list[tuple[str, str]],
        index: int,
    ) -> str | None:
        if (
            index + 3 < len(tokens)
            and tokens[index + 1][1] == "("
        ):
            module_type, module_name = tokens[index + 2]

            if (
                module_type == "string"
                and tokens[index + 3][1] == ")"
            ):
                return module_name

        return None

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