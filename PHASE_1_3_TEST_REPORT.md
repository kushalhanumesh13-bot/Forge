# Forge Phase 1-3 Test and Function Audit

Date: 2026-09-22

## Executive Summary

The complete available pytest suite was executed against the release state.

```text
76 passed, 2 skipped in 7.80s
```

The two skipped tests are Windows-environment symlink tests. They skip only when symbolic-link creation is unavailable.

The release commits under test are:

- `840bff2` - codebase understanding
- `53a7b18` - deterministic engineering brain
- `af9eed2` - Phase 1-3 security hardening

The repository contains no external coverage package. A standard-library trace attempt did not produce a reliable result, so this report does not claim runtime line or function coverage percentages. The function inventory below is static AST inventory; pytest results are behavioral test results, not proof that every function was called.

## Application Inventory

| File | Source lines | AST functions/methods |
|---|---:|---:|
| `app/__init__.py` | 0 | 0 |
| `app/api/repository.py` | 17 | 1 |
| `app/main.py` | 20 | 1 |
| `app/services/analyzer.py` | 1,570 | 39 |
| `app/services/codebase.py` | 1,025 | 50 |
| `app/services/engineering_brain.py` | 676 | 28 |
| `app/services/repository.py` | 62 | 3 |
| **Total** | **3,370** | **122** |

## Function Inventory

### `app/api/repository.py`

- `analyze_repository`

### `app/main.py`

- `health_check`

### `app/services/repository.py`

- `RepositoryService.__init__`
- `RepositoryService.get_files`
- `RepositoryService._is_ignored`

### `app/services/analyzer.py`

- `RepositoryAnalyzer.__init__`
- `RepositoryAnalyzer.analyze`
- `RepositoryAnalyzer.get_codebase_context`
- `RepositoryAnalyzer._parse_python`
- `RepositoryAnalyzer._read_source_file`
- `RepositoryAnalyzer._build_repository_index`
- `RepositoryAnalyzer._detect_architecture`
- `RepositoryAnalyzer._detect_architecture.paths_with_component`
- `RepositoryAnalyzer._python_module_roots`
- `RepositoryAnalyzer._analyze_python_imports`
- `RepositoryAnalyzer._analyze_python_code_structure`
- `RepositoryAnalyzer._structure_definition`
- `RepositoryAnalyzer._collect_python_methods`
- `RepositoryAnalyzer._assignment_names`
- `RepositoryAnalyzer._assignment_names.collect`
- `RepositoryAnalyzer._decorator_name`
- `RepositoryAnalyzer._analyze_git`
- `RepositoryAnalyzer._run_git_command`
- `RepositoryAnalyzer._parse_git_status`
- `RepositoryAnalyzer._analyze_readme`
- `RepositoryAnalyzer._contains_python_main_guard`
- `RepositoryAnalyzer._detect_package_entry_points`
- `RepositoryAnalyzer._parse_package_json`
- `RepositoryAnalyzer._package_export_values`
- `RepositoryAnalyzer._resolve_entry_point`
- `RepositoryAnalyzer._dependency_file_kind`
- `RepositoryAnalyzer._read_dependency_file`
- `RepositoryAnalyzer._detect_dependencies`
- `RepositoryAnalyzer._detect_requirements_dependencies`
- `RepositoryAnalyzer._detect_pyproject_dependencies`
- `RepositoryAnalyzer._detect_package_dependencies`
- `RepositoryAnalyzer._dependency_name`
- `RepositoryAnalyzer._detect_frameworks`
- `RepositoryAnalyzer._detect_python_frameworks`
- `RepositoryAnalyzer._detect_javascript_frameworks`
- `RepositoryAnalyzer._tokenize_javascript`
- `RepositoryAnalyzer._imported_module_name`
- `RepositoryAnalyzer._required_module_name`
- `RepositoryAnalyzer._detect_project_type`

### `app/services/codebase.py`

- `CodebaseUnderstandingBuilder.__init__`
- `CodebaseUnderstandingBuilder.build`
- `CodebaseUnderstandingBuilder._files`
- `CodebaseUnderstandingBuilder._important_files`
- `CodebaseUnderstandingBuilder._module_name`
- `CodebaseUnderstandingBuilder._module_to_paths`
- `CodebaseUnderstandingBuilder._symbols_for_module`
- `CodebaseUnderstandingBuilder._symbols_for_module.add_class`
- `CodebaseUnderstandingBuilder._symbol_record`
- `CodebaseUnderstandingBuilder._imports_for_module`
- `CodebaseUnderstandingBuilder._import_record`
- `CodebaseUnderstandingBuilder._absolute_module`
- `CodebaseUnderstandingBuilder._resolve_import`
- `CodebaseUnderstandingBuilder._unambiguous_paths`
- `CodebaseUnderstandingBuilder._build_module`
- `CodebaseUnderstandingBuilder._relationships_for`
- `CodebaseUnderstandingBuilder._graph_for`
- `CodebaseUnderstandingBuilder._references_for_module`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor.__init__`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor.source_symbol`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor.visit_ClassDef`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor.visit_FunctionDef`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor.visit_AsyncFunctionDef`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor._visit_function`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor.visit_Call`
- `CodebaseUnderstandingBuilder._references_for_module.Visitor.visit_Name`
- `CodebaseUnderstandingBuilder._references_for_module.single_resolved_path`
- `CodebaseUnderstandingBuilder._references_for_module.make_reference`
- `CodebaseUnderstandingBuilder._entry_point_context`
- `CodebaseUnderstandingBuilder._module_name_for_path`
- `CodebaseUnderstandingBuilder._components`
- `CodebaseUnderstandingBuilder._components.matches`
- `CodebaseUnderstandingBuilder._summaries`
- `CodebaseUnderstandingBuilder._role_for_path`
- `CodebaseUnderstandingBuilder._visibility`
- `CodebaseUnderstandingBuilder._decorator_name`
- `CodebaseUnderstandingBuilder._assignment_names`
- `CodebaseUnderstandingBuilder._assignment_names.collect`
- `CodebaseContext.__init__`
- `CodebaseContext.understanding`
- `CodebaseContext.symbols_named`
- `CodebaseContext.symbols_in_file`
- `CodebaseContext.module`
- `CodebaseContext.modules_importing`
- `CodebaseContext.modules_imported_by`
- `CodebaseContext.local_dependencies`
- `CodebaseContext.local_dependents`
- `CodebaseContext.entry_point`
- `CodebaseContext.focused`
- `CodebaseContext._path`

### `app/services/engineering_brain.py`

- `EngineeringBrain.__init__`
- `EngineeringBrain.parse_task`
- `EngineeringBrain.classify_task`
- `EngineeringBrain.retrieve_context`
- `EngineeringBrain.rank_relevance`
- `EngineeringBrain.analyze_scope`
- `EngineeringBrain.analyze_impact`
- `EngineeringBrain.detect_ambiguity`
- `EngineeringBrain.analyze_risks`
- `EngineeringBrain.generate_test_strategy`
- `EngineeringBrain.generate_plan`
- `EngineeringBrain._rank_files`
- `EngineeringBrain._plan_steps`
- `EngineeringBrain._assumptions`
- `EngineeringBrain._plan_confidence`
- `EngineeringBrain._related_tests`
- `EngineeringBrain._related_entry_points`
- `EngineeringBrain._explicit_target_paths`
- `EngineeringBrain._components_for_paths`
- `EngineeringBrain._layers_for_paths`
- `EngineeringBrain._component_names_for_path`
- `EngineeringBrain._all_paths_and_names`
- `EngineeringBrain._is_normalized_task`
- `EngineeringBrain._normalize_type`
- `EngineeringBrain._text`
- `EngineeringBrain._strings`
- `EngineeringBrain._keywords`
- `EngineeringBrain._term_matches`

## Test Coverage Areas

### Phase 1

The existing analyzer and repository tests cover scanning, ignored paths, file counts, project types, tests, metadata, technologies, frameworks, dependencies, lockfiles, entry points, configurations, README parsing, Git metadata, imports, code structure, architecture, indexing, malformed input, and empty repositories.

### Phase 2

The existing codebase tests cover AST modules, symbols, methods, async functions, decorators, visibility, line ranges, packages, `src` layouts, local/external/standard-library/unresolved imports, references, entry points, components, summaries, lookups, determinism, invalid files, empty repositories, and unreadable sources.

### Phase 3

The Engineering Brain tests cover task normalization, classification, scope, ranking, context retrieval, impact, ambiguity, risks, assumptions, plans, step dependencies, test strategy, determinism, invalid repositories, and empty repositories.

### Hardening

`tests/test_hardening.py` covers:

- symlink file isolation
- symlink directory isolation
- repository roots named ignored directories
- defensive lookup copies
- ambiguous local modules
- explainable relationship ranking
- public API risk detection
- JSON serialization
- bounded task input
- oversized source files
- oversized metadata files

## Security Checks

Static scans found no `shell=True`, `os.system`, unsafe `Popen`, `eval`, `exec`, `pickle`, unsafe YAML loading, external AI API, or network client usage.

Git commands use fixed argument arrays, `shell=False` behavior, captured output, and a timeout. Repository source is parsed statically and is not executed.

Tracked-file checks found no `.env`, credential, token, private-key, virtual-environment, cache, or build-artifact paths.

## Known Limitations

- `coverage.py` is not installed in the project environment, so numerical runtime coverage was not measured.
- The standard-library trace collector did not produce a reliable report and was not used to make coverage claims.
- Static analysis cannot fully model Python reflection, dynamic imports, monkey-patching, or runtime dispatch.
- Symlink tests skip when the Windows environment cannot create symbolic links.
- Large repositories still incur normal traversal and AST-analysis costs.

## Final Verification

The behavioral release gate passed:

```text
76 passed, 2 skipped in 7.80s
```

The report is an audit artifact, not a claim that every one of the 122 functions was independently invoked. For true line/function coverage percentages, install `coverage.py` in the development environment and rerun the suite with `pytest --cov=app --cov-report=term-missing`.
