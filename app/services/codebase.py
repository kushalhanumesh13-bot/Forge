"""Deterministic, local codebase-understanding helpers for Forge.

The structures in this module intentionally describe only facts that can be
established from a repository scan and Python's AST.  They are designed to be
small enough to retain in memory and to be reused by later operations without
rescanning a repository.
"""

from __future__ import annotations

import ast
import copy
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PYTHON_SUFFIX = ".py"


class CodebaseUnderstandingBuilder:
    """Build the JSON-serializable Phase 2 model from an analyzer scan."""

    def __init__(
        self,
        repository_root: Path,
        files: list[Path],
        python_trees: dict[str, ast.AST | None],
        parse_status: dict[str, str],
        imports: dict[str, dict[str, list[str]]],
        code_structure: dict[str, dict[str, list[dict[str, Any]]]],
        entry_points: list[str],
        architecture: dict[str, Any],
        configurations: list[str],
        frameworks_by_file: dict[str, list[str]],
        index: dict[str, Any],
    ) -> None:
        self.repository_root = repository_root
        self.files = files
        self.python_trees = python_trees
        self.parse_status = parse_status
        self.import_analysis = imports
        self.code_structure = code_structure
        self.entry_points = sorted(entry_points)
        self.architecture = architecture
        self.configurations = sorted(configurations)
        self.frameworks_by_file = frameworks_by_file
        self.index = index
        self.python_paths = sorted(
            path.relative_to(repository_root).as_posix()
            for path in files
            if path.suffix == PYTHON_SUFFIX
        )
        self.module_names = {
            path: self._module_name(path)
            for path in self.python_paths
        }
        self.module_to_paths = self._module_to_paths()

    def build(self) -> dict[str, Any]:
        """Return an empty-safe, stable understanding object."""
        modules: list[dict[str, Any]] = []
        symbols: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []
        graph: dict[str, dict[str, list[str]]] = {}
        references: list[dict[str, Any]] = []

        for path in self.python_paths:
            tree = self.python_trees.get(path)
            module_symbols, module_constants = self._symbols_for_module(path, tree)
            symbols.extend(module_symbols)
            import_records = self._imports_for_module(path, tree)
            module = self._build_module(
                path,
                module_symbols,
                module_constants,
                import_records,
            )
            modules.append(module)
            relationships.extend(self._relationships_for(path, import_records))
            graph[path] = self._graph_for(import_records)
            references.extend(
                self._references_for_module(
                    path,
                    tree,
                    module_symbols,
                    import_records,
                )
            )

        modules.sort(key=lambda item: item["path"])
        symbols.sort(
            key=lambda item: (
                item["file"],
                item["line"],
                item["parent"] or "",
                item["name"],
                item["type"],
            )
        )
        relationships.sort(
            key=lambda item: (
                item["source"],
                item["dependency_type"],
                item["target"],
                item["line"],
            )
        )
        references.sort(
            key=lambda item: (
                item["source_file"],
                item["line"],
                item["kind"],
                item["target"],
            )
        )

        summaries = self._summaries(modules)
        files = self._files()
        return {
            "files": files,
            "modules": modules,
            "symbols": symbols,
            "relationships": relationships,
            "dependency_graph": dict(sorted(graph.items())),
            "references": references,
            "entry_point_context": self._entry_point_context(modules),
            "components": self._components(),
            "layers": list(self.architecture.get("layers", [])),
            "test_files": [
                file["path"]
                for file in files
                if file["is_test"]
                and file["language"] in {"python", "javascript", "typescript"}
            ],
            "configuration_files": self.configurations,
            "important_files": self._important_files(files),
            "summaries": dict(sorted(summaries.items())),
        }

    def _files(self) -> list[dict[str, Any]]:
        """Expose concise file facts from the existing repository index."""
        records = []
        entry_points = set(self.entry_points)
        for indexed_file in self.index.get("files", []):
            path = indexed_file["path"]
            records.append(
                {
                    "path": path,
                    "language": indexed_file["language"],
                    "file_type": indexed_file["file_type"],
                    "is_test": indexed_file["is_test"],
                    "is_entry_point": path in entry_points,
                    "module": self.module_names.get(path),
                }
            )
        return sorted(records, key=lambda item: item["path"])

    def _important_files(
        self,
        files: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        important = []
        for file in files:
            roles = []
            if file["is_entry_point"]:
                roles.append("entry_point")
            if file["is_test"] and file["language"] in {
                "python",
                "javascript",
                "typescript",
            }:
                roles.append("test")
            if file["path"] in self.configurations:
                roles.append("configuration")
            if file["file_type"] in {"metadata", "lockfile"}:
                roles.append(file["file_type"])
            if roles:
                important.append({"path": file["path"], "roles": roles})
        return important

    def _module_name(self, path: str) -> str | None:
        parts = path.removesuffix(PYTHON_SUFFIX).split("/")
        if parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts) or None

    def _module_to_paths(self) -> dict[str, list[str]]:
        """Map importable names to repository paths, including src layouts."""
        result: dict[str, list[str]] = defaultdict(list)
        for path, module_name in self.module_names.items():
            if not module_name:
                continue
            result[module_name].append(path)

        # ``src`` is commonly a source root rather than an importable package.
        # Do not let its convenient alias override a real root-level module.
        for path, module_name in self.module_names.items():
            if not module_name or not module_name.startswith("src."):
                continue
            alias = module_name.removeprefix("src.")
            if alias not in result:
                result[alias].append(path)

        return {
            name: sorted(set(paths))
            for name, paths in sorted(result.items())
        }

    def _symbols_for_module(
        self,
        path: str,
        tree: ast.AST | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if tree is None:
            return [], []

        symbols: list[dict[str, Any]] = []
        constants: list[dict[str, Any]] = []

        def add_class(node: ast.ClassDef, parent: str | None = None) -> None:
            class_parent = parent
            symbols.append(
                self._symbol_record(path, node, "class", class_parent)
            )
            qualified_name = (
                f"{parent}.{node.name}" if parent else node.name
            )
            for child in node.body:
                if isinstance(child, ast.ClassDef):
                    add_class(child, qualified_name)
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        self._symbol_record(path, child, "method", qualified_name)
                    )

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                add_class(node)
            elif isinstance(node, ast.FunctionDef):
                symbols.append(self._symbol_record(path, node, "function", None))
            elif isinstance(node, ast.AsyncFunctionDef):
                symbols.append(
                    self._symbol_record(path, node, "async_function", None)
                )
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                for name in self._assignment_names(node):
                    if name.isupper():
                        constants.append({"name": name, "line": node.lineno})

        return symbols, sorted(constants, key=lambda item: (item["line"], item["name"]))

    def _symbol_record(
        self,
        path: str,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        symbol_type: str,
        parent: str | None,
    ) -> dict[str, Any]:
        return {
            "name": node.name,
            "type": symbol_type,
            "file": path,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", None),
            "parent": parent,
            "decorators": sorted(
                self._decorator_name(decorator)
                for decorator in node.decorator_list
            ),
            "visibility": self._visibility(node.name),
            "async": isinstance(node, ast.AsyncFunctionDef),
        }

    def _imports_for_module(
        self,
        path: str,
        tree: ast.AST | None,
    ) -> list[dict[str, Any]]:
        if tree is None:
            return []

        records: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    records.append(
                        self._import_record(
                            path,
                            alias.name,
                            node.lineno,
                            "import",
                            [alias.name],
                            alias.asname,
                            [
                                {
                                    "name": alias.name,
                                    "asname": alias.asname,
                                }
                            ],
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                raw_module = "." * node.level + (node.module or "")
                names = [alias.name for alias in node.names]
                records.append(
                    self._import_record(
                        path,
                        raw_module,
                        node.lineno,
                        "from",
                        names,
                        None,
                        [
                            {"name": alias.name, "asname": alias.asname}
                            for alias in node.names
                        ],
                    )
                )

        return sorted(
            records,
            key=lambda item: (
                item["line"],
                item["module"],
                item["statement"],
                item["names"],
            ),
        )

    def _import_record(
        self,
        source_path: str,
        raw_module: str,
        line: int,
        statement: str,
        names: list[str],
        alias: str | None,
        bindings: list[dict[str, str | None]],
    ) -> dict[str, Any]:
        absolute_module = self._absolute_module(source_path, raw_module)
        resolved_paths = self._resolve_import(
            absolute_module,
            names if statement == "from" else [],
        )
        root = (absolute_module or raw_module).lstrip(".").split(".", 1)[0]

        if resolved_paths:
            dependency_type = "local"
        elif raw_module.startswith("."):
            dependency_type = "unresolved"
        elif absolute_module in self.module_to_paths:
            dependency_type = "unresolved"
        elif root in sys.stdlib_module_names:
            dependency_type = "standard_library"
        elif root:
            dependency_type = "third_party"
        else:
            dependency_type = "unresolved"

        return {
            "module": raw_module,
            "resolved_module": absolute_module,
            "statement": statement,
            "names": sorted(names),
            "alias": alias,
            "bindings": sorted(bindings, key=lambda item: item["name"]),
            "line": line,
            "dependency_type": dependency_type,
            "resolved_paths": resolved_paths,
        }

    def _absolute_module(self, source_path: str, raw_module: str) -> str | None:
        if not raw_module.startswith("."):
            return raw_module or None

        current_module = self.module_names.get(source_path)
        if not current_module:
            return None

        is_initializer = (
            source_path.endswith("/__init__.py")
            or source_path == "__init__.py"
        )
        package_parts = current_module.split(".")
        if not is_initializer:
            package_parts.pop()

        level = len(raw_module) - len(raw_module.lstrip("."))
        if level > len(package_parts) + 1:
            return None
        base_parts = package_parts[: len(package_parts) - max(level - 1, 0)]
        suffix = raw_module.lstrip(".")
        if suffix:
            base_parts.extend(suffix.split("."))
        return ".".join(base_parts) or None

    def _resolve_import(
        self,
        module_name: str | None,
        imported_names: list[str],
    ) -> list[str]:
        if not module_name:
            return []

        child_candidates = []
        for name in imported_names:
            if name != "*":
                child_candidates.append(f"{module_name}.{name}")

        resolved_children = []
        for candidate in child_candidates:
            resolved_children.extend(self._unambiguous_paths(candidate))
        if resolved_children:
            return sorted(set(resolved_children))

        return self._unambiguous_paths(module_name)

    def _unambiguous_paths(self, module_name: str) -> list[str]:
        paths = self.module_to_paths.get(module_name, [])
        return list(paths) if len(paths) == 1 else []

    def _build_module(
        self,
        path: str,
        symbols: list[dict[str, Any]],
        constants: list[dict[str, Any]],
        import_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        top_level = [symbol for symbol in symbols if symbol["parent"] is None]
        assignments = self.code_structure.get(path, {}).get("global_assignments", [])
        defined_names = [symbol["name"] for symbol in top_level] + [
            assignment["name"] for assignment in assignments
        ]
        public_symbols = sorted(
            {name for name in defined_names if self._visibility(name) == "public"}
        )
        private_symbols = sorted(
            {name for name in defined_names if self._visibility(name) == "private"}
        )
        return {
            "path": path,
            "module": self.module_names[path],
            "language": "python",
            "parse_status": self.parse_status.get(path, "invalid"),
            "imports": import_records,
            "imported_modules": self.import_analysis.get(path, {}).get(
                "imports",
                [],
            ),
            "classes": [
                symbol for symbol in symbols if symbol["type"] == "class"
            ],
            "functions": [
                symbol
                for symbol in symbols
                if symbol["type"] in {"function", "async_function"}
            ],
            "methods": [
                symbol for symbol in symbols if symbol["type"] == "method"
            ],
            "async_functions": [
                symbol for symbol in symbols if symbol["async"]
            ],
            "constants": constants,
            "public_symbols": public_symbols,
            "private_symbols": private_symbols,
        }

    def _relationships_for(
        self,
        source_path: str,
        import_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        relationships = []
        for record in import_records:
            targets = record["resolved_paths"] or [
                record["resolved_module"] or record["module"]
            ]
            for target in targets:
                relationships.append(
                    {
                        "source": source_path,
                        "target": target,
                        "relationship": "imports",
                        "dependency_type": record["dependency_type"],
                        "module": record["module"],
                        "line": record["line"],
                    }
                )
        return relationships

    def _graph_for(
        self,
        import_records: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        local = set()
        external = set()
        standard_library = set()
        unresolved = set()
        for record in import_records:
            dependency_type = record["dependency_type"]
            if dependency_type == "local":
                local.update(record["resolved_paths"])
            else:
                name = record["resolved_module"] or record["module"]
                root = name.lstrip(".").split(".", 1)[0]
                if not root:
                    continue
                if dependency_type == "third_party":
                    external.add(root)
                elif dependency_type == "standard_library":
                    standard_library.add(root)
                else:
                    unresolved.add(name)
        return {
            "local": sorted(local),
            "external": sorted(external),
            "standard_library": sorted(standard_library),
            "unresolved": sorted(unresolved),
        }

    def _references_for_module(
        self,
        path: str,
        tree: ast.AST | None,
        symbols: list[dict[str, Any]],
        import_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if tree is None:
            return []

        local_top_level = {
            symbol["name"]: symbol
            for symbol in symbols
            if symbol["parent"] is None
        }
        methods_by_class: dict[str, set[str]] = defaultdict(set)
        for symbol in symbols:
            if symbol["type"] == "method" and symbol["parent"]:
                methods_by_class[symbol["parent"]].add(symbol["name"])

        imported_names: dict[str, dict[str, Any]] = {}
        module_aliases: dict[str, dict[str, Any]] = {}
        for record in import_records:
            if record["statement"] == "import":
                if record["alias"]:
                    module_aliases[record["alias"]] = record
                elif "." not in record["module"]:
                    module_aliases[record["module"]] = record
            else:
                for binding in record["bindings"]:
                    if binding["name"] != "*":
                        imported_names[
                            binding["asname"] or binding["name"]
                        ] = record

        references: list[dict[str, Any]] = []

        class Visitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.class_stack: list[str] = []
                self.symbol_stack: list[str] = []

            @property
            def source_symbol(self) -> str | None:
                return self.symbol_stack[-1] if self.symbol_stack else None

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                qualified = ".".join(self.class_stack + [node.name])
                self.class_stack.append(node.name)
                self.symbol_stack.append(qualified)
                self.generic_visit(node)
                self.symbol_stack.pop()
                self.class_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._visit_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._visit_function(node)

            def _visit_function(
                self,
                node: ast.FunctionDef | ast.AsyncFunctionDef,
            ) -> None:
                parent = ".".join(self.class_stack)
                name = f"{parent}.{node.name}" if parent else node.name
                self.symbol_stack.append(name)
                self.generic_visit(node)
                self.symbol_stack.pop()

            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name in local_top_level:
                        references.append(
                            make_reference(
                                node,
                                "direct_call",
                                name,
                                path,
                                "high",
                                self.source_symbol,
                            )
                        )
                    elif name in imported_names:
                        record = imported_names[name]
                        target_file = single_resolved_path(record)
                        references.append(
                            make_reference(
                                node,
                                "imported_symbol_call",
                                name,
                                target_file,
                                "high" if target_file else "medium",
                                self.source_symbol,
                            )
                        )
                elif isinstance(node.func, ast.Attribute):
                    value = node.func.value
                    if (
                        isinstance(value, ast.Name)
                        and value.id == "self"
                        and self.class_stack
                    ):
                        class_name = ".".join(self.class_stack)
                        if node.func.attr in methods_by_class.get(class_name, set()):
                            references.append(
                                make_reference(
                                    node,
                                    "method_call",
                                    f"{class_name}.{node.func.attr}",
                                    path,
                                    "high",
                                    self.source_symbol,
                                )
                            )
                    elif isinstance(value, ast.Name) and value.id in module_aliases:
                        record = module_aliases[value.id]
                        target_file = single_resolved_path(record)
                        references.append(
                            make_reference(
                                node,
                                "imported_member_call",
                                f"{value.id}.{node.func.attr}",
                                target_file,
                                "medium" if target_file else "low",
                                self.source_symbol,
                            )
                        )
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load) and node.id in imported_names:
                    record = imported_names[node.id]
                    references.append(
                        make_reference(
                            node,
                            "imported_symbol_reference",
                            node.id,
                            single_resolved_path(record),
                            "high" if single_resolved_path(record) else "medium",
                            self.source_symbol,
                        )
                    )
                self.generic_visit(node)

        def single_resolved_path(record: dict[str, Any]) -> str | None:
            paths = record["resolved_paths"]
            return paths[0] if len(paths) == 1 else None

        def make_reference(
            node: ast.AST,
            kind: str,
            target: str,
            target_file: str | None,
            confidence: str,
            source_symbol: str | None,
        ) -> dict[str, Any]:
            return {
                "source_file": path,
                "source_symbol": source_symbol,
                "target": target,
                "target_file": target_file,
                "kind": kind,
                "line": getattr(node, "lineno", None),
                "confidence": confidence,
            }

        Visitor().visit(tree)
        return references

    def _entry_point_context(
        self,
        modules: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        modules_by_path = {module["path"]: module for module in modules}
        contexts = []
        for path in self.entry_points:
            module = modules_by_path.get(path)
            import_records = module["imports"] if module else []
            contexts.append(
                {
                    "path": path,
                    "module": (
                        module["module"]
                        if module
                        else self._module_name_for_path(path)
                    ),
                    "frameworks": self.frameworks_by_file.get(path, []),
                    "symbols": module["public_symbols"] if module else [],
                    "imports": sorted(
                        {record["module"] for record in import_records}
                    ),
                    "local_imports": sorted(
                        {
                            target
                            for record in import_records
                            for target in record["resolved_paths"]
                        }
                    ),
                }
            )
        return contexts

    def _module_name_for_path(self, path: str) -> str | None:
        return self.module_names.get(path)

    def _components(self) -> list[dict[str, Any]]:
        source_paths = set(self.python_paths)
        source_paths.update(
            path.relative_to(self.repository_root).as_posix()
            for path in self.files
            if path.suffix in {".js", ".ts"}
        )

        def matches(names: set[str]) -> list[str]:
            return sorted(
                path
                for path in source_paths
                if any(
                    part.lower() in names
                    for part in path.split("/") + [Path(path).stem]
                )
            )

        components = []
        layer_paths = {
            "api": matches({"api", "routes", "routers", "controllers"}),
            "services": matches({"service", "services"}),
            "repository": matches(
                {"repository", "repositories", "data", "persistence", "dao"}
            ),
            "tests": sorted(
                path
                for path in source_paths
                if "test" in Path(path).name.lower()
                or "tests" in {part.lower() for part in path.split("/")}
            ),
            "configuration": self.configurations,
        }
        for layer in self.architecture.get("layers", []):
            files = layer_paths.get(layer, [])
            components.append(
                {
                    "name": layer,
                    "kind": "layer",
                    "files": files,
                    "evidence": [
                        evidence
                        for evidence in self.architecture.get("evidence", [])
                        if layer in evidence.lower()
                    ],
                }
            )

        component_paths = {
            "python_package": sorted(
                path
                for path in self.python_paths
                if path.endswith("/__init__.py") or path == "__init__.py"
            ),
            "backend": sorted(self.python_paths),
            "frontend": matches({"frontend", "client", "web", "ui"}),
        }
        for component in self.architecture.get("components", []):
            components.append(
                {
                    "name": component,
                    "kind": "component",
                    "files": component_paths.get(component, []),
                    "evidence": [
                        evidence
                        for evidence in self.architecture.get("evidence", [])
                        if component.replace("_", " ") in evidence.lower()
                    ],
                }
            )
        return sorted(components, key=lambda item: (item["kind"], item["name"]))

    def _summaries(self, modules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        modules_by_path = {module["path"]: module for module in modules}
        summaries = {}
        for path in sorted(
            file_path.relative_to(self.repository_root).as_posix()
            for file_path in self.files
            if file_path.suffix in {".py", ".js", ".ts"}
        ):
            module = modules_by_path.get(path)
            language = {".py": "python", ".js": "javascript", ".ts": "typescript"}.get(
                Path(path).suffix,
                "other",
            )
            summary = {
                "language": language,
                "role": self._role_for_path(path),
                "frameworks": self.frameworks_by_file.get(path, []),
            }
            if module:
                summary.update(
                    {
                        "classes": [item["name"] for item in module["classes"]],
                        "functions": [item["name"] for item in module["functions"]],
                        "imports": module["imported_modules"],
                        "parse_status": module["parse_status"],
                    }
                )
            else:
                summary.update(
                    {
                        "classes": [],
                        "functions": [],
                        "imports": [],
                        "parse_status": "not_supported",
                    }
                )
            summaries[path] = summary
        return summaries

    def _role_for_path(self, path: str) -> str:
        parts = {part.lower() for part in path.split("/")}
        if "tests" in parts or "test" in Path(path).stem.lower():
            return "test"
        if parts & {"api", "routes", "routers", "controllers"}:
            return "api"
        if parts & {"service", "services"}:
            return "service"
        if parts & {"repository", "repositories", "data", "persistence", "dao"}:
            return "repository"
        return "module"

    @staticmethod
    def _visibility(name: str) -> str:
        return "private" if name.startswith("_") else "public"

    @staticmethod
    def _decorator_name(decorator: ast.AST) -> str:
        try:
            return ast.unparse(decorator)
        except (AttributeError, ValueError):
            return (
                decorator.id
                if isinstance(decorator, ast.Name)
                else type(decorator).__name__
            )

    @staticmethod
    def _assignment_names(node: ast.AST) -> list[str]:
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]

        names: list[str] = []

        def collect(target: ast.AST) -> None:
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for element in target.elts:
                    collect(element)

        for target in targets:
            collect(target)
        return names


class CodebaseContext:
    """Small composable lookup API over a completed understanding object."""

    def __init__(self, understanding: dict[str, Any]) -> None:
        self._understanding = copy.deepcopy(understanding)
        self._modules = {
            module["path"]: module
            for module in self._understanding.get("modules", [])
        }
        self._symbols = self._understanding.get("symbols", [])
        self._relationships = self._understanding.get("relationships", [])
        self._graph = self._understanding.get("dependency_graph", {})
        self._entry_points = {
            entry_point["path"]: entry_point
            for entry_point in self._understanding.get("entry_point_context", [])
        }

    @property
    def understanding(self) -> dict[str, Any]:
        """Return a copy so callers cannot mutate the cached model."""
        return copy.deepcopy(self._understanding)

    def symbols_named(self, name: str) -> list[dict[str, Any]]:
        return copy.deepcopy(
            [symbol for symbol in self._symbols if symbol["name"] == name]
        )

    def symbols_in_file(self, path: str) -> list[dict[str, Any]]:
        normalized = self._path(path)
        return copy.deepcopy(
            [symbol for symbol in self._symbols if symbol["file"] == normalized]
        )

    def module(self, path_or_module: str) -> dict[str, Any] | None:
        normalized = self._path(path_or_module)
        if normalized in self._modules:
            return copy.deepcopy(self._modules[normalized])
        for module in self._modules.values():
            if module["module"] == path_or_module:
                return copy.deepcopy(module)
        return None

    def modules_importing(self, path_or_module: str) -> list[str]:
        target_module = self.module(path_or_module)
        target_path = (
            target_module["path"]
            if target_module
            else self._path(path_or_module)
        )
        matches = {
            relationship["source"]
            for relationship in self._relationships
            if relationship["dependency_type"] == "local"
            and relationship["target"] == target_path
        }
        return sorted(matches)

    def modules_imported_by(self, path_or_module: str) -> list[str]:
        module = self.module(path_or_module)
        if not module:
            return []
        return sorted(
            {
                record["resolved_module"] or record["module"]
                for record in module["imports"]
            }
        )

    def local_dependencies(self, path_or_module: str) -> list[str]:
        module = self.module(path_or_module)
        if not module:
            return []
        return list(self._graph.get(module["path"], {}).get("local", []))

    def local_dependents(self, path_or_module: str) -> list[str]:
        return self.modules_importing(path_or_module)

    def entry_point(self, path_or_module: str) -> dict[str, Any] | None:
        normalized = self._path(path_or_module)
        entry_point = self._entry_points.get(normalized)
        if entry_point:
            return copy.deepcopy(entry_point)

        module = self.module(path_or_module)
        return (
            copy.deepcopy(self._entry_points[module["path"]])
            if module and module["path"] in self._entry_points
            else None
        )

    def focused(
        self,
        *,
        file_path: str | None = None,
        symbol_name: str | None = None,
        module_name: str | None = None,
        entry_point: str | None = None,
    ) -> dict[str, Any]:
        """Return related facts without rescanning or reparsing source files."""
        path = file_path or module_name
        module = self.module(path) if path else None
        selected_path = (
            module["path"]
            if module
            else self._path(file_path)
            if file_path
            else None
        )
        return copy.deepcopy({
            "module": module,
            "symbols": (
                self.symbols_named(symbol_name)
                if symbol_name
                else self.symbols_in_file(selected_path)
                if selected_path
                else []
            ),
            "local_dependencies": (
                self.local_dependencies(selected_path) if selected_path else []
            ),
            "local_dependents": (
                self.local_dependents(selected_path) if selected_path else []
            ),
            "entry_point": self.entry_point(
                entry_point or selected_path or module_name
            ) if (entry_point or selected_path or module_name) else None,
        })

    @staticmethod
    def _path(path: str | None) -> str:
        return (path or "").replace("\\", "/")


# An explicit service alias makes the intended reuse point clear to callers.
CodebaseContextService = CodebaseContext
